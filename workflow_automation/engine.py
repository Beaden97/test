"""Core workflow engine that orchestrates everything."""

import asyncio
import logging
import signal
from datetime import datetime
from pathlib import Path
from typing import Callable

import yaml

from .workflow import Workflow, WorkflowStatus
from .triggers import Trigger, CronTrigger, FileTrigger, WebhookTrigger
from .actions import ShellAction, HttpAction, PythonAction
from .scheduler import Scheduler

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Main engine that manages and executes workflows."""

    def __init__(self, config_dir: str | Path | None = None):
        self.workflows: dict[str, Workflow] = {}
        self.scheduler = Scheduler()
        self.config_dir = Path(config_dir) if config_dir else None
        self.running = False
        self._tasks: list[asyncio.Task] = []
        self._webhook_server = None
        self._file_observers: list = []

        # Execution history
        self.history: list[dict] = []

    def register(self, workflow: Workflow) -> None:
        """Register a workflow with the engine."""
        self.workflows[workflow.id] = workflow
        logger.info(f"Registered workflow: {workflow.name} ({workflow.id})")

        # Set up triggers
        for trigger in workflow.triggers:
            self._setup_trigger(workflow, trigger)

    def _setup_trigger(self, workflow: Workflow, trigger: Trigger) -> None:
        """Set up a trigger for a workflow."""
        if isinstance(trigger, CronTrigger):
            self.scheduler.add_cron_job(
                trigger.cron_expression,
                lambda w=workflow: asyncio.create_task(self._execute_workflow(w, {"trigger": "cron"}))
            )
        elif isinstance(trigger, FileTrigger):
            trigger.set_callback(
                lambda event, w=workflow: asyncio.create_task(
                    self._execute_workflow(w, {"trigger": "file", "event": event})
                )
            )
            self._file_observers.append(trigger)

    async def _execute_workflow(self, workflow: Workflow, trigger_data: dict) -> None:
        """Execute a workflow and record history."""
        if not workflow.enabled:
            logger.info(f"Skipping disabled workflow: {workflow.name}")
            return

        start_time = datetime.now()
        status = WorkflowStatus.RUNNING
        error = None

        try:
            context = await workflow.execute(trigger_data)
            status = WorkflowStatus.COMPLETED
        except Exception as e:
            status = WorkflowStatus.FAILED
            error = str(e)
            logger.error(f"Workflow '{workflow.name}' failed: {e}")

        # Record in history
        self.history.append({
            "workflow_id": workflow.id,
            "workflow_name": workflow.name,
            "status": status.value,
            "started_at": start_time.isoformat(),
            "completed_at": datetime.now().isoformat(),
            "error": error,
            "trigger_data": trigger_data
        })

    def load_from_yaml(self, file_path: str | Path) -> Workflow:
        """Load a workflow from a YAML file."""
        path = Path(file_path)
        with open(path) as f:
            config = yaml.safe_load(f)

        workflow = Workflow(
            name=config.get("name", path.stem),
            description=config.get("description", ""),
            enabled=config.get("enabled", True)
        )

        # Parse triggers
        for trigger_config in config.get("triggers", []):
            trigger = self._parse_trigger(trigger_config)
            if trigger:
                workflow.add_trigger(trigger)

        # Parse steps
        for step_config in config.get("steps", []):
            action = self._parse_action(step_config.get("action", {}))
            if action:
                workflow.add_step(
                    name=step_config.get("name", "unnamed"),
                    action=action,
                    condition=step_config.get("condition"),
                    on_failure=step_config.get("on_failure", "stop"),
                    retry_count=step_config.get("retry_count", 0),
                    retry_delay=step_config.get("retry_delay", 1.0)
                )

        self.register(workflow)
        return workflow

    def _parse_trigger(self, config: dict) -> Trigger | None:
        """Parse a trigger from config."""
        trigger_type = config.get("type")

        if trigger_type == "cron":
            return CronTrigger(config.get("expression", "* * * * *"))
        elif trigger_type == "file":
            return FileTrigger(
                path=config.get("path", "."),
                patterns=config.get("patterns", ["*"]),
                events=config.get("events", ["created", "modified"])
            )
        elif trigger_type == "webhook":
            return WebhookTrigger(
                path=config.get("path", "/webhook"),
                method=config.get("method", "POST")
            )
        return None

    def _parse_action(self, config: dict) -> "Action | None":
        """Parse an action from config."""
        action_type = config.get("type")

        if action_type == "shell":
            return ShellAction(
                command=config.get("command", "echo 'No command'"),
                timeout=config.get("timeout", 60),
                shell=config.get("shell", "/bin/bash")
            )
        elif action_type == "http":
            return HttpAction(
                url=config.get("url", ""),
                method=config.get("method", "GET"),
                headers=config.get("headers", {}),
                body=config.get("body")
            )
        elif action_type == "python":
            return PythonAction(
                code=config.get("code", ""),
                function=config.get("function")
            )
        return None

    def load_directory(self, directory: str | Path | None = None) -> list[Workflow]:
        """Load all workflows from a directory."""
        dir_path = Path(directory) if directory else self.config_dir
        if not dir_path or not dir_path.exists():
            return []

        workflows = []
        for file_path in dir_path.glob("*.yaml"):
            try:
                workflow = self.load_from_yaml(file_path)
                workflows.append(workflow)
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")

        for file_path in dir_path.glob("*.yml"):
            try:
                workflow = self.load_from_yaml(file_path)
                workflows.append(workflow)
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")

        return workflows

    async def run_once(self, workflow_id: str, trigger_data: dict | None = None) -> None:
        """Run a specific workflow once."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        await self._execute_workflow(workflow, trigger_data or {})

    async def start(self) -> None:
        """Start the workflow engine."""
        if self.running:
            return

        self.running = True
        logger.info("Starting workflow engine...")

        # Start the scheduler
        self._tasks.append(asyncio.create_task(self.scheduler.run()))

        # Start file observers
        for observer in self._file_observers:
            observer.start()

        logger.info(f"Engine running with {len(self.workflows)} workflows")

    async def stop(self) -> None:
        """Stop the workflow engine."""
        if not self.running:
            return

        self.running = False
        logger.info("Stopping workflow engine...")

        # Stop file observers
        for observer in self._file_observers:
            observer.stop()

        # Cancel tasks
        for task in self._tasks:
            task.cancel()

        self._tasks.clear()
        logger.info("Engine stopped")

    def get_status(self) -> dict:
        """Get the current status of the engine."""
        return {
            "running": self.running,
            "workflows": len(self.workflows),
            "executions": len(self.history),
            "workflows_list": [
                {
                    "id": w.id,
                    "name": w.name,
                    "enabled": w.enabled,
                    "triggers": len(w.triggers),
                    "steps": len(w.steps),
                    "run_count": w.run_count,
                    "last_run": w.last_run.isoformat() if w.last_run else None
                }
                for w in self.workflows.values()
            ]
        }

    def __repr__(self) -> str:
        return f"WorkflowEngine(workflows={len(self.workflows)}, running={self.running})"

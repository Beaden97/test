"""Workflow definition and execution."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid
import logging

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Status of a workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowContext:
    """Context passed between workflow steps."""
    workflow_id: str
    run_id: str
    trigger_data: dict = field(default_factory=dict)
    variables: dict = field(default_factory=dict)
    results: dict = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)

    def set(self, key: str, value: Any) -> None:
        """Set a variable in the context."""
        self.variables[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a variable from the context."""
        return self.variables.get(key, default)

    def store_result(self, step_name: str, result: Any) -> None:
        """Store the result of a step."""
        self.results[step_name] = result


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    name: str
    action: "Action"
    condition: str | None = None
    on_failure: str = "stop"  # stop, continue, retry
    retry_count: int = 0
    retry_delay: float = 1.0


class Workflow:
    """A workflow consisting of triggers and steps."""

    def __init__(
        self,
        name: str,
        description: str = "",
        enabled: bool = True
    ):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.description = description
        self.enabled = enabled
        self.triggers: list = []
        self.steps: list[WorkflowStep] = []
        self.created_at = datetime.now()
        self.last_run: datetime | None = None
        self.run_count = 0

    def add_trigger(self, trigger: "Trigger") -> "Workflow":
        """Add a trigger to the workflow."""
        self.triggers.append(trigger)
        return self

    def add_step(
        self,
        name: str,
        action: "Action",
        condition: str | None = None,
        on_failure: str = "stop",
        retry_count: int = 0,
        retry_delay: float = 1.0
    ) -> "Workflow":
        """Add a step to the workflow."""
        step = WorkflowStep(
            name=name,
            action=action,
            condition=condition,
            on_failure=on_failure,
            retry_count=retry_count,
            retry_delay=retry_delay
        )
        self.steps.append(step)
        return self

    async def execute(self, trigger_data: dict | None = None) -> WorkflowContext:
        """Execute all steps in the workflow."""
        run_id = str(uuid.uuid4())[:8]
        context = WorkflowContext(
            workflow_id=self.id,
            run_id=run_id,
            trigger_data=trigger_data or {}
        )

        logger.info(f"Starting workflow '{self.name}' (run: {run_id})")
        self.last_run = datetime.now()
        self.run_count += 1

        for step in self.steps:
            if step.condition and not self._evaluate_condition(step.condition, context):
                logger.info(f"Skipping step '{step.name}' - condition not met")
                continue

            logger.info(f"Executing step '{step.name}'")

            attempts = 0
            max_attempts = step.retry_count + 1

            while attempts < max_attempts:
                try:
                    result = await step.action.execute(context)
                    context.store_result(step.name, result)
                    logger.info(f"Step '{step.name}' completed successfully")
                    break
                except Exception as e:
                    attempts += 1
                    logger.error(f"Step '{step.name}' failed (attempt {attempts}): {e}")

                    if attempts < max_attempts:
                        import asyncio
                        await asyncio.sleep(step.retry_delay)
                    elif step.on_failure == "stop":
                        raise
                    elif step.on_failure == "continue":
                        context.store_result(step.name, {"error": str(e)})

        logger.info(f"Workflow '{self.name}' completed (run: {run_id})")
        return context

    def _evaluate_condition(self, condition: str, context: WorkflowContext) -> bool:
        """Evaluate a condition expression."""
        try:
            return eval(condition, {"context": context, "results": context.results})
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"Workflow(name='{self.name}', steps={len(self.steps)}, triggers={len(self.triggers)})"

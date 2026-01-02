"""Action system for workflow steps - shell, HTTP, Python code."""

from abc import ABC, abstractmethod
from typing import Any
import asyncio
import subprocess
import logging
import json

import aiohttp

from .workflow import WorkflowContext

logger = logging.getLogger(__name__)


class Action(ABC):
    """Base class for all actions."""

    @abstractmethod
    async def execute(self, context: WorkflowContext) -> Any:
        """Execute the action and return a result."""
        pass


class ShellAction(Action):
    """Execute a shell command."""

    def __init__(
        self,
        command: str,
        timeout: float = 60,
        shell: str = "/bin/bash",
        capture_output: bool = True,
        env: dict[str, str] | None = None
    ):
        self.command = command
        self.timeout = timeout
        self.shell = shell
        self.capture_output = capture_output
        self.env = env or {}

    def _interpolate(self, text: str, context: WorkflowContext) -> str:
        """Interpolate variables in the command."""
        result = text

        # Replace {{variable}} patterns
        for key, value in context.variables.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))

        # Replace {{trigger.key}} patterns
        for key, value in context.trigger_data.items():
            result = result.replace(f"{{{{trigger.{key}}}}}", str(value))

        # Replace {{results.step.key}} patterns
        for step_name, step_result in context.results.items():
            if isinstance(step_result, dict):
                for key, value in step_result.items():
                    result = result.replace(
                        f"{{{{results.{step_name}.{key}}}}}",
                        str(value)
                    )

        return result

    async def execute(self, context: WorkflowContext) -> dict:
        """Execute the shell command."""
        command = self._interpolate(self.command, context)
        logger.debug(f"Executing shell command: {command}")

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE if self.capture_output else None,
                stderr=asyncio.subprocess.PIPE if self.capture_output else None,
                executable=self.shell
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )

            return {
                "returncode": process.returncode,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else "",
                "success": process.returncode == 0
            }

        except asyncio.TimeoutError:
            process.kill()
            raise TimeoutError(f"Command timed out after {self.timeout}s")

    def __repr__(self) -> str:
        return f"ShellAction(command='{self.command[:50]}...')"


class HttpAction(Action):
    """Make an HTTP request."""

    def __init__(
        self,
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: Any = None,
        timeout: float = 30,
        json_response: bool = True
    ):
        self.url = url
        self.method = method.upper()
        self.headers = headers or {}
        self.body = body
        self.timeout = timeout
        self.json_response = json_response

    def _interpolate(self, value: Any, context: WorkflowContext) -> Any:
        """Interpolate variables in values."""
        if isinstance(value, str):
            result = value
            for key, val in context.variables.items():
                result = result.replace(f"{{{{{key}}}}}", str(val))
            return result
        elif isinstance(value, dict):
            return {k: self._interpolate(v, context) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._interpolate(v, context) for v in value]
        return value

    async def execute(self, context: WorkflowContext) -> dict:
        """Execute the HTTP request."""
        url = self._interpolate(self.url, context)
        headers = self._interpolate(self.headers, context)
        body = self._interpolate(self.body, context)

        logger.debug(f"Making HTTP {self.method} request to {url}")

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            kwargs = {"headers": headers}

            if body and self.method in ("POST", "PUT", "PATCH"):
                if isinstance(body, dict):
                    kwargs["json"] = body
                else:
                    kwargs["data"] = body

            async with session.request(self.method, url, **kwargs) as response:
                result = {
                    "status": response.status,
                    "headers": dict(response.headers),
                    "success": 200 <= response.status < 300
                }

                if self.json_response:
                    try:
                        result["body"] = await response.json()
                    except Exception:
                        result["body"] = await response.text()
                else:
                    result["body"] = await response.text()

                return result

    def __repr__(self) -> str:
        return f"HttpAction(method='{self.method}', url='{self.url}')"


class PythonAction(Action):
    """Execute Python code."""

    def __init__(
        self,
        code: str = "",
        function: str | None = None
    ):
        self.code = code
        self.function = function

    async def execute(self, context: WorkflowContext) -> Any:
        """Execute the Python code."""
        # Create execution namespace
        namespace = {
            "context": context,
            "variables": context.variables,
            "trigger_data": context.trigger_data,
            "results": context.results,
            "asyncio": asyncio,
            "json": json,
        }

        # Execute the code
        exec(self.code, namespace)

        # If a function is specified, call it
        if self.function and self.function in namespace:
            func = namespace[self.function]
            if asyncio.iscoroutinefunction(func):
                return await func(context)
            else:
                return func(context)

        # Return any 'result' variable defined
        return namespace.get("result")

    def __repr__(self) -> str:
        return f"PythonAction(function='{self.function}')"


class ConditionalAction(Action):
    """Execute different actions based on a condition."""

    def __init__(
        self,
        condition: str,
        if_true: Action,
        if_false: Action | None = None
    ):
        self.condition = condition
        self.if_true = if_true
        self.if_false = if_false

    async def execute(self, context: WorkflowContext) -> Any:
        """Execute the appropriate action based on condition."""
        result = eval(self.condition, {
            "context": context,
            "variables": context.variables,
            "results": context.results
        })

        if result:
            return await self.if_true.execute(context)
        elif self.if_false:
            return await self.if_false.execute(context)

        return None

    def __repr__(self) -> str:
        return f"ConditionalAction(condition='{self.condition}')"


class ParallelAction(Action):
    """Execute multiple actions in parallel."""

    def __init__(self, actions: list[Action]):
        self.actions = actions

    async def execute(self, context: WorkflowContext) -> list[Any]:
        """Execute all actions in parallel."""
        tasks = [action.execute(context) for action in self.actions]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def __repr__(self) -> str:
        return f"ParallelAction(actions={len(self.actions)})"


class SequentialAction(Action):
    """Execute multiple actions in sequence."""

    def __init__(self, actions: list[Action]):
        self.actions = actions

    async def execute(self, context: WorkflowContext) -> list[Any]:
        """Execute all actions in sequence."""
        results = []
        for action in self.actions:
            result = await action.execute(context)
            results.append(result)
        return results

    def __repr__(self) -> str:
        return f"SequentialAction(actions={len(self.actions)})"


class DelayAction(Action):
    """Wait for a specified duration."""

    def __init__(self, seconds: float):
        self.seconds = seconds

    async def execute(self, context: WorkflowContext) -> dict:
        """Wait for the specified duration."""
        await asyncio.sleep(self.seconds)
        return {"delayed": self.seconds}

    def __repr__(self) -> str:
        return f"DelayAction(seconds={self.seconds})"


class LogAction(Action):
    """Log a message."""

    def __init__(self, message: str, level: str = "info"):
        self.message = message
        self.level = level.lower()

    async def execute(self, context: WorkflowContext) -> dict:
        """Log the message."""
        # Interpolate variables
        message = self.message
        for key, value in context.variables.items():
            message = message.replace(f"{{{{{key}}}}}", str(value))

        log_func = getattr(logger, self.level, logger.info)
        log_func(message)

        return {"logged": message, "level": self.level}

    def __repr__(self) -> str:
        return f"LogAction(message='{self.message[:30]}...')"

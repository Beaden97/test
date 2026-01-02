"""Workflow Automation - Your personal robot army for intelligent workflows."""

__version__ = "1.0.0"

from .engine import WorkflowEngine
from .workflow import Workflow
from .triggers import Trigger, CronTrigger, FileTrigger, WebhookTrigger
from .actions import Action, ShellAction, HttpAction, PythonAction
from .scheduler import Scheduler

__all__ = [
    "WorkflowEngine",
    "Workflow",
    "Trigger",
    "CronTrigger",
    "FileTrigger",
    "WebhookTrigger",
    "Action",
    "ShellAction",
    "HttpAction",
    "PythonAction",
    "Scheduler",
]

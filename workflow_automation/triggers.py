"""Trigger system for workflows - cron, file watchers, webhooks."""

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Callable, Any
import logging
import fnmatch

from croniter import croniter
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

logger = logging.getLogger(__name__)


class Trigger(ABC):
    """Base class for all triggers."""

    def __init__(self):
        self.callback: Callable | None = None
        self.enabled = True

    def set_callback(self, callback: Callable) -> None:
        """Set the callback function to execute when triggered."""
        self.callback = callback

    @abstractmethod
    def check(self) -> bool:
        """Check if the trigger condition is met."""
        pass

    def fire(self, data: dict | None = None) -> None:
        """Fire the trigger."""
        if self.callback and self.enabled:
            self.callback(data or {})


class CronTrigger(Trigger):
    """Trigger based on cron expressions."""

    def __init__(self, cron_expression: str):
        super().__init__()
        self.cron_expression = cron_expression
        self._cron = croniter(cron_expression, datetime.now())
        self._next_run = self._cron.get_next(datetime)

    def check(self) -> bool:
        """Check if it's time to fire."""
        now = datetime.now()
        if now >= self._next_run:
            self._next_run = self._cron.get_next(datetime)
            return True
        return False

    def get_next_run(self) -> datetime:
        """Get the next scheduled run time."""
        return self._next_run

    def __repr__(self) -> str:
        return f"CronTrigger('{self.cron_expression}')"


class FileEventHandler(FileSystemEventHandler):
    """Handler for file system events."""

    def __init__(self, trigger: "FileTrigger"):
        self.trigger = trigger

    def _should_handle(self, event: FileSystemEvent) -> bool:
        """Check if we should handle this event."""
        if event.is_directory:
            return False

        # Check event type
        event_type = event.event_type
        if event_type not in self.trigger.events:
            return False

        # Check patterns
        filename = Path(event.src_path).name
        for pattern in self.trigger.patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True

        return False

    def on_created(self, event: FileSystemEvent) -> None:
        if self._should_handle(event):
            self.trigger.fire({
                "event_type": "created",
                "path": event.src_path,
                "is_directory": event.is_directory
            })

    def on_modified(self, event: FileSystemEvent) -> None:
        if self._should_handle(event):
            self.trigger.fire({
                "event_type": "modified",
                "path": event.src_path,
                "is_directory": event.is_directory
            })

    def on_deleted(self, event: FileSystemEvent) -> None:
        if self._should_handle(event):
            self.trigger.fire({
                "event_type": "deleted",
                "path": event.src_path,
                "is_directory": event.is_directory
            })

    def on_moved(self, event: FileSystemEvent) -> None:
        if self._should_handle(event):
            self.trigger.fire({
                "event_type": "moved",
                "src_path": event.src_path,
                "dest_path": getattr(event, "dest_path", None),
                "is_directory": event.is_directory
            })


class FileTrigger(Trigger):
    """Trigger based on file system events."""

    def __init__(
        self,
        path: str | Path,
        patterns: list[str] | None = None,
        events: list[str] | None = None,
        recursive: bool = True
    ):
        super().__init__()
        self.path = Path(path)
        self.patterns = patterns or ["*"]
        self.events = events or ["created", "modified", "deleted", "moved"]
        self.recursive = recursive
        self._observer: Observer | None = None
        self._handler = FileEventHandler(self)

    def check(self) -> bool:
        """File triggers are event-based, not poll-based."""
        return False

    def start(self) -> None:
        """Start watching for file changes."""
        if self._observer:
            return

        self._observer = Observer()
        self._observer.schedule(
            self._handler,
            str(self.path),
            recursive=self.recursive
        )
        self._observer.start()
        logger.info(f"Started file watcher on {self.path}")

    def stop(self) -> None:
        """Stop watching for file changes."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info(f"Stopped file watcher on {self.path}")

    def __repr__(self) -> str:
        return f"FileTrigger(path='{self.path}', patterns={self.patterns})"


class WebhookTrigger(Trigger):
    """Trigger based on HTTP webhook calls."""

    def __init__(
        self,
        path: str = "/webhook",
        method: str = "POST",
        secret: str | None = None
    ):
        super().__init__()
        self.path = path
        self.method = method.upper()
        self.secret = secret
        self._registered = False

    def check(self) -> bool:
        """Webhook triggers are event-based, not poll-based."""
        return False

    def validate_request(self, headers: dict, body: bytes) -> bool:
        """Validate the webhook request."""
        if not self.secret:
            return True

        import hmac
        import hashlib

        signature = headers.get("X-Webhook-Signature", "")
        expected = hmac.new(
            self.secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    def __repr__(self) -> str:
        return f"WebhookTrigger(path='{self.path}', method='{self.method}')"


class IntervalTrigger(Trigger):
    """Trigger that fires at regular intervals."""

    def __init__(self, seconds: float = 60):
        super().__init__()
        self.interval = seconds
        self._last_run = datetime.now()

    def check(self) -> bool:
        """Check if the interval has elapsed."""
        now = datetime.now()
        elapsed = (now - self._last_run).total_seconds()
        if elapsed >= self.interval:
            self._last_run = now
            return True
        return False

    def __repr__(self) -> str:
        return f"IntervalTrigger(seconds={self.interval})"


class ManualTrigger(Trigger):
    """Trigger that only fires when manually invoked."""

    def __init__(self, name: str = "manual"):
        super().__init__()
        self.name = name

    def check(self) -> bool:
        """Manual triggers never auto-fire."""
        return False

    def invoke(self, data: dict | None = None) -> None:
        """Manually invoke this trigger."""
        self.fire(data)

    def __repr__(self) -> str:
        return f"ManualTrigger(name='{self.name}')"

"""Scheduler for timed and cron-based jobs."""

import asyncio
from datetime import datetime
from typing import Callable, Any
import logging
from dataclasses import dataclass, field

from croniter import croniter

logger = logging.getLogger(__name__)


@dataclass
class ScheduledJob:
    """A scheduled job."""
    id: str
    name: str
    callback: Callable
    cron_expression: str | None = None
    interval_seconds: float | None = None
    next_run: datetime = field(default_factory=datetime.now)
    enabled: bool = True
    run_count: int = 0
    last_run: datetime | None = None

    def calculate_next_run(self) -> None:
        """Calculate the next run time."""
        if self.cron_expression:
            cron = croniter(self.cron_expression, datetime.now())
            self.next_run = cron.get_next(datetime)
        elif self.interval_seconds:
            self.next_run = datetime.now()
            self.next_run = datetime.fromtimestamp(
                self.next_run.timestamp() + self.interval_seconds
            )


class Scheduler:
    """Manages scheduled jobs with cron expressions and intervals."""

    def __init__(self, check_interval: float = 1.0):
        self.jobs: dict[str, ScheduledJob] = {}
        self.check_interval = check_interval
        self.running = False
        self._job_counter = 0

    def add_cron_job(
        self,
        cron_expression: str,
        callback: Callable,
        name: str | None = None
    ) -> str:
        """Add a job with a cron expression."""
        self._job_counter += 1
        job_id = f"cron_{self._job_counter}"

        cron = croniter(cron_expression, datetime.now())
        next_run = cron.get_next(datetime)

        job = ScheduledJob(
            id=job_id,
            name=name or job_id,
            callback=callback,
            cron_expression=cron_expression,
            next_run=next_run
        )

        self.jobs[job_id] = job
        logger.info(f"Added cron job '{job.name}' ({cron_expression}), next run: {next_run}")
        return job_id

    def add_interval_job(
        self,
        seconds: float,
        callback: Callable,
        name: str | None = None,
        run_immediately: bool = False
    ) -> str:
        """Add a job that runs at regular intervals."""
        self._job_counter += 1
        job_id = f"interval_{self._job_counter}"

        if run_immediately:
            next_run = datetime.now()
        else:
            next_run = datetime.fromtimestamp(
                datetime.now().timestamp() + seconds
            )

        job = ScheduledJob(
            id=job_id,
            name=name or job_id,
            callback=callback,
            interval_seconds=seconds,
            next_run=next_run
        )

        self.jobs[job_id] = job
        logger.info(f"Added interval job '{job.name}' (every {seconds}s)")
        return job_id

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job."""
        if job_id in self.jobs:
            job = self.jobs.pop(job_id)
            logger.info(f"Removed job '{job.name}'")
            return True
        return False

    def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job."""
        if job_id in self.jobs:
            self.jobs[job_id].enabled = False
            logger.info(f"Paused job '{self.jobs[job_id].name}'")
            return True
        return False

    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job.enabled = True
            job.calculate_next_run()
            logger.info(f"Resumed job '{job.name}'")
            return True
        return False

    async def run(self) -> None:
        """Run the scheduler loop."""
        self.running = True
        logger.info("Scheduler started")

        while self.running:
            now = datetime.now()

            for job in list(self.jobs.values()):
                if not job.enabled:
                    continue

                if now >= job.next_run:
                    logger.debug(f"Running job '{job.name}'")
                    job.run_count += 1
                    job.last_run = now

                    try:
                        result = job.callback()
                        if asyncio.iscoroutine(result):
                            asyncio.create_task(result)
                    except Exception as e:
                        logger.error(f"Job '{job.name}' failed: {e}")

                    job.calculate_next_run()

            await asyncio.sleep(self.check_interval)

        logger.info("Scheduler stopped")

    def stop(self) -> None:
        """Stop the scheduler."""
        self.running = False

    def get_jobs(self) -> list[dict]:
        """Get information about all jobs."""
        return [
            {
                "id": job.id,
                "name": job.name,
                "cron": job.cron_expression,
                "interval": job.interval_seconds,
                "enabled": job.enabled,
                "next_run": job.next_run.isoformat(),
                "run_count": job.run_count,
                "last_run": job.last_run.isoformat() if job.last_run else None
            }
            for job in self.jobs.values()
        ]

    def get_next_job(self) -> ScheduledJob | None:
        """Get the next job to run."""
        enabled_jobs = [j for j in self.jobs.values() if j.enabled]
        if not enabled_jobs:
            return None
        return min(enabled_jobs, key=lambda j: j.next_run)

    def __repr__(self) -> str:
        return f"Scheduler(jobs={len(self.jobs)}, running={self.running})"

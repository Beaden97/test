"""
Email Analyzer Module

This analyzes your emails and groups them to help you
make decisions about what to keep, archive, or delete.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from .client import Email


@dataclass
class SenderStats:
    """
    Statistics about emails from a specific sender.
    """
    email: str
    name: str
    total_count: int = 0
    unread_count: int = 0
    oldest_date: Optional[datetime] = None
    newest_date: Optional[datetime] = None
    total_size_bytes: int = 0
    sample_subjects: list[str] = field(default_factory=list)
    email_ids: list[str] = field(default_factory=list)

    @property
    def size_mb(self) -> float:
        return self.total_size_bytes / (1024 * 1024)

    def __str__(self):
        return f"{self.name} ({self.email}): {self.total_count} emails, {self.size_mb:.1f} MB"


@dataclass
class CleanupSuggestion:
    """
    A suggestion for cleaning up emails.
    """
    category: str  # e.g., "old_newsletters", "large_attachments"
    description: str
    email_ids: list[str]
    estimated_space_mb: float
    priority: int  # 1 = high, 2 = medium, 3 = low
    action: str  # "archive", "delete", "label"

    def __str__(self):
        return f"[{self.priority}] {self.description} ({len(self.email_ids)} emails, {self.estimated_space_mb:.1f} MB)"


class EmailAnalyzer:
    """
    Analyzes emails and provides cleanup suggestions.

    This is your helper for understanding what's in your inbox
    and what might be safe to clean up.
    """

    # Common newsletter/marketing patterns
    NEWSLETTER_PATTERNS = [
        'unsubscribe',
        'email preferences',
        'opt-out',
        'newsletter',
        'weekly digest',
        'daily digest',
    ]

    # Common promotional sender patterns
    PROMO_SENDERS = [
        'noreply',
        'no-reply',
        'marketing',
        'newsletter',
        'promo',
        'deals',
        'offers',
    ]

    def __init__(self, emails: list[Email]):
        """
        Create an analyzer for a set of emails.

        Args:
            emails: List of emails to analyze
        """
        self.emails = emails
        self._sender_stats: dict[str, SenderStats] = {}
        self._analyzed = False

    def analyze(self) -> dict:
        """
        Run full analysis on the emails.

        Returns:
            Dictionary with analysis results
        """
        self._analyze_senders()
        self._analyzed = True

        return {
            'total_emails': len(self.emails),
            'total_size_mb': sum(e.size_bytes for e in self.emails) / (1024 * 1024),
            'unread_count': sum(1 for e in self.emails if e.is_unread),
            'sender_count': len(self._sender_stats),
            'date_range': self._get_date_range(),
        }

    def _analyze_senders(self):
        """
        Group emails by sender and calculate statistics.
        """
        for email in self.emails:
            sender_key = email.sender_email.lower()

            if sender_key not in self._sender_stats:
                self._sender_stats[sender_key] = SenderStats(
                    email=email.sender_email,
                    name=email.sender
                )

            stats = self._sender_stats[sender_key]
            stats.total_count += 1
            stats.total_size_bytes += email.size_bytes
            stats.email_ids.append(email.id)

            if email.is_unread:
                stats.unread_count += 1

            if stats.oldest_date is None or email.date < stats.oldest_date:
                stats.oldest_date = email.date
            if stats.newest_date is None or email.date > stats.newest_date:
                stats.newest_date = email.date

            if len(stats.sample_subjects) < 3:
                stats.sample_subjects.append(email.subject)

    def _get_date_range(self) -> dict:
        """
        Get the date range of emails.
        """
        if not self.emails:
            return {'oldest': None, 'newest': None}

        dates = [e.date for e in self.emails]
        return {
            'oldest': min(dates),
            'newest': max(dates)
        }

    def get_top_senders(self, limit: int = 20) -> list[SenderStats]:
        """
        Get the senders with the most emails.

        Args:
            limit: Maximum number of senders to return

        Returns:
            List of SenderStats, sorted by email count (descending)
        """
        if not self._analyzed:
            self.analyze()

        sorted_senders = sorted(
            self._sender_stats.values(),
            key=lambda s: s.total_count,
            reverse=True
        )
        return sorted_senders[:limit]

    def get_largest_senders(self, limit: int = 20) -> list[SenderStats]:
        """
        Get the senders using the most storage space.

        Args:
            limit: Maximum number of senders to return

        Returns:
            List of SenderStats, sorted by total size (descending)
        """
        if not self._analyzed:
            self.analyze()

        sorted_senders = sorted(
            self._sender_stats.values(),
            key=lambda s: s.total_size_bytes,
            reverse=True
        )
        return sorted_senders[:limit]

    def get_sender_stats(self, email_address: str) -> Optional[SenderStats]:
        """
        Get statistics for a specific sender.
        """
        if not self._analyzed:
            self.analyze()

        return self._sender_stats.get(email_address.lower())

    def find_newsletters(self) -> list[SenderStats]:
        """
        Find likely newsletter/marketing senders.

        Returns:
            List of senders that look like newsletters
        """
        if not self._analyzed:
            self.analyze()

        newsletters = []

        for stats in self._sender_stats.values():
            # Check if sender looks like a newsletter
            sender_lower = stats.email.lower()
            is_newsletter = False

            # Check sender patterns
            for pattern in self.PROMO_SENDERS:
                if pattern in sender_lower:
                    is_newsletter = True
                    break

            # Check if they send frequently (more than 5 emails)
            if stats.total_count >= 5:
                # Check subject patterns
                for subject in stats.sample_subjects:
                    subject_lower = subject.lower()
                    for pattern in self.NEWSLETTER_PATTERNS:
                        if pattern in subject_lower:
                            is_newsletter = True
                            break

            if is_newsletter:
                newsletters.append(stats)

        return sorted(newsletters, key=lambda s: s.total_count, reverse=True)

    def find_old_emails(self, days: int = 365) -> list[Email]:
        """
        Find emails older than a certain number of days.

        Args:
            days: Age threshold in days

        Returns:
            List of old emails
        """
        if not self.emails:
            return []

        # Get timezone from first email if available
        sample_tz = self.emails[0].date.tzinfo if self.emails[0].date.tzinfo else None
        cutoff = datetime.now(sample_tz) - timedelta(days=days)

        return [e for e in self.emails if e.date < cutoff]

    def find_large_emails(self, min_size_mb: float = 5.0) -> list[Email]:
        """
        Find emails larger than a certain size.

        Args:
            min_size_mb: Minimum size in megabytes

        Returns:
            List of large emails
        """
        min_bytes = min_size_mb * 1024 * 1024
        return sorted(
            [e for e in self.emails if e.size_bytes >= min_bytes],
            key=lambda e: e.size_bytes,
            reverse=True
        )

    def get_cleanup_suggestions(self) -> list[CleanupSuggestion]:
        """
        Get smart suggestions for cleaning up your inbox.

        Returns:
            List of cleanup suggestions, sorted by priority
        """
        if not self._analyzed:
            self.analyze()

        suggestions = []

        # Build email lookup map by ID
        email_by_id = {e.id: e for e in self.emails}

        # Get timezone-aware cutoff for 90 days ago
        sample_tz = self.emails[0].date.tzinfo if self.emails and self.emails[0].date.tzinfo else None
        cutoff_90_days = datetime.now(sample_tz) - timedelta(days=90)

        # Suggestion 1: Old newsletters
        newsletters = self.find_newsletters()
        for nl in newsletters[:5]:  # Top 5 newsletter senders
            old_emails = [eid for eid in nl.email_ids
                         if eid in email_by_id and email_by_id[eid].date < cutoff_90_days]
            if old_emails:
                suggestions.append(CleanupSuggestion(
                    category="old_newsletters",
                    description=f"Old newsletters from {nl.name}",
                    email_ids=old_emails,
                    estimated_space_mb=len(old_emails) * (nl.total_size_bytes / nl.total_count) / (1024 * 1024),
                    priority=2,
                    action="archive"
                ))

        # Suggestion 2: Large emails
        large_emails = self.find_large_emails(min_size_mb=10)
        if large_emails:
            suggestions.append(CleanupSuggestion(
                category="large_emails",
                description=f"Emails larger than 10MB",
                email_ids=[e.id for e in large_emails],
                estimated_space_mb=sum(e.size_bytes for e in large_emails) / (1024 * 1024),
                priority=1,
                action="review"
            ))

        # Suggestion 3: Very old emails
        old_emails = self.find_old_emails(days=730)  # 2 years
        if old_emails:
            suggestions.append(CleanupSuggestion(
                category="very_old",
                description="Emails older than 2 years",
                email_ids=[e.id for e in old_emails],
                estimated_space_mb=sum(e.size_bytes for e in old_emails) / (1024 * 1024),
                priority=3,
                action="archive"
            ))

        # Suggestion 4: High-volume senders
        top_senders = self.get_top_senders(limit=10)
        for sender in top_senders:
            if sender.total_count > 50:
                suggestions.append(CleanupSuggestion(
                    category="high_volume",
                    description=f"Review {sender.total_count} emails from {sender.name}",
                    email_ids=sender.email_ids,
                    estimated_space_mb=sender.size_mb,
                    priority=2,
                    action="review"
                ))

        return sorted(suggestions, key=lambda s: s.priority)

    def group_by_domain(self) -> dict[str, list[SenderStats]]:
        """
        Group senders by their email domain.

        Returns:
            Dictionary mapping domain to list of sender stats
        """
        if not self._analyzed:
            self.analyze()

        domains = defaultdict(list)

        for stats in self._sender_stats.values():
            if '@' in stats.email:
                domain = stats.email.split('@')[1].lower()
                domains[domain].append(stats)

        # Sort senders within each domain by count
        for domain in domains:
            domains[domain].sort(key=lambda s: s.total_count, reverse=True)

        return dict(domains)

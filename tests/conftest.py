"""
Shared fixtures and factories for Gmail Cleanup tests.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass, field
import json
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from gmail_cleanup.client import Email, Label, GmailClient
from gmail_cleanup.analyzer import EmailAnalyzer, SenderStats, CleanupSuggestion
from gmail_cleanup.rules import Rule, RuleManager


# ============================================================================
# Email Factories
# ============================================================================

class EmailFactory:
    """Factory for creating test Email objects."""

    _counter = 0

    @classmethod
    def create(
        cls,
        id: str = None,
        thread_id: str = None,
        subject: str = "Test Subject",
        sender: str = "Test Sender",
        sender_email: str = "sender@example.com",
        recipient: str = "me@example.com",
        date: datetime = None,
        snippet: str = "Email preview snippet...",
        labels: list = None,
        is_unread: bool = False,
        size_bytes: int = 1024,
    ) -> Email:
        """Create a test email with sensible defaults."""
        cls._counter += 1
        return Email(
            id=id or f"msg_{cls._counter}",
            thread_id=thread_id or f"thread_{cls._counter}",
            subject=subject,
            sender=sender,
            sender_email=sender_email,
            recipient=recipient,
            date=date or datetime.now(timezone.utc),
            snippet=snippet,
            labels=labels or ["INBOX"],
            is_unread=is_unread,
            size_bytes=size_bytes,
        )

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> list[Email]:
        """Create multiple emails with the same attributes."""
        return [cls.create(**kwargs) for _ in range(count)]

    @classmethod
    def create_newsletter(cls, sender_domain: str = "newsletter.com", **kwargs) -> Email:
        """Create an email that looks like a newsletter."""
        defaults = {
            "sender": f"Newsletter <noreply@{sender_domain}>",
            "sender_email": f"noreply@{sender_domain}",
            "subject": "Weekly Digest - Unsubscribe to opt-out",
        }
        defaults.update(kwargs)
        return cls.create(**defaults)

    @classmethod
    def create_large_email(cls, size_mb: float = 10.0, **kwargs) -> Email:
        """Create a large email."""
        kwargs['size_bytes'] = int(size_mb * 1024 * 1024)
        return cls.create(**kwargs)

    @classmethod
    def create_old_email(cls, days_old: int = 400, **kwargs) -> Email:
        """Create an old email."""
        kwargs['date'] = datetime.now(timezone.utc) - timedelta(days=days_old)
        return cls.create(**kwargs)

    @classmethod
    def reset_counter(cls):
        """Reset the counter for deterministic IDs."""
        cls._counter = 0


class LabelFactory:
    """Factory for creating test Label objects."""

    @classmethod
    def create(
        cls,
        id: str = None,
        name: str = "TestLabel",
        type: str = "user",
        messages_total: int = 0,
        messages_unread: int = 0,
    ) -> Label:
        """Create a test label."""
        return Label(
            id=id or f"Label_{name}",
            name=name,
            type=type,
            messages_total=messages_total,
            messages_unread=messages_unread,
        )

    @classmethod
    def create_system_label(cls, name: str) -> Label:
        """Create a system label like INBOX, SENT, etc."""
        return cls.create(id=name, name=name, type="system")


class RuleFactory:
    """Factory for creating test Rule objects."""

    @classmethod
    def create(
        cls,
        name: str = "Test Rule",
        from_email: str = None,
        to_email: str = None,
        subject_contains: str = None,
        has_words: str = None,
        add_label: str = None,
        remove_label: str = None,
        archive: bool = False,
        mark_read: bool = False,
        star: bool = False,
        never_spam: bool = False,
        forward_to: str = None,
        gmail_filter_id: str = None,
    ) -> Rule:
        """Create a test rule."""
        return Rule(
            name=name,
            from_email=from_email,
            to_email=to_email,
            subject_contains=subject_contains,
            has_words=has_words,
            add_label=add_label,
            remove_label=remove_label,
            archive=archive,
            mark_read=mark_read,
            star=star,
            never_spam=never_spam,
            forward_to=forward_to,
            gmail_filter_id=gmail_filter_id,
        )


# ============================================================================
# Mock Gmail API Fixtures
# ============================================================================

@pytest.fixture
def mock_gmail_service():
    """Create a mock Gmail API service."""
    service = MagicMock()

    # Setup users().messages() chain
    messages = MagicMock()
    service.users.return_value.messages.return_value = messages

    # Setup users().labels() chain
    labels = MagicMock()
    service.users.return_value.labels.return_value = labels

    # Setup users().settings().filters() chain
    filters = MagicMock()
    service.users.return_value.settings.return_value.filters.return_value = filters

    return service


@pytest.fixture
def mock_messages_list(mock_gmail_service):
    """Setup mock for messages.list()."""
    def setup_list(messages_data):
        mock_gmail_service.users().messages().list.return_value.execute.return_value = {
            'messages': messages_data,
            'nextPageToken': None
        }
    return setup_list


@pytest.fixture
def mock_message_get(mock_gmail_service):
    """Setup mock for messages.get()."""
    def setup_get(message_data):
        mock_gmail_service.users().messages().get.return_value.execute.return_value = message_data
    return setup_get


# ============================================================================
# Gmail Client Fixtures
# ============================================================================

@pytest.fixture
def gmail_client(mock_gmail_service):
    """Create a GmailClient with mocked service in dry_run mode."""
    return GmailClient(mock_gmail_service, dry_run=True)


@pytest.fixture
def gmail_client_live(mock_gmail_service):
    """Create a GmailClient with mocked service in live mode (dry_run=False)."""
    return GmailClient(mock_gmail_service, dry_run=False)


# ============================================================================
# Analyzer Fixtures
# ============================================================================

@pytest.fixture
def sample_emails():
    """Create a sample list of emails for analysis."""
    EmailFactory.reset_counter()
    return [
        EmailFactory.create(
            sender="Alice",
            sender_email="alice@company.com",
            is_unread=True,
            size_bytes=5000
        ),
        EmailFactory.create(
            sender="Alice",
            sender_email="alice@company.com",
            size_bytes=3000
        ),
        EmailFactory.create(
            sender="Bob",
            sender_email="bob@other.com",
            is_unread=True,
            size_bytes=10000
        ),
        EmailFactory.create(
            sender="Newsletter",
            sender_email="noreply@newsletter.com",
            subject="Weekly Digest - Click to unsubscribe",
            size_bytes=2000
        ),
    ]


@pytest.fixture
def email_analyzer(sample_emails):
    """Create an EmailAnalyzer with sample emails."""
    return EmailAnalyzer(sample_emails)


@pytest.fixture
def empty_analyzer():
    """Create an EmailAnalyzer with no emails."""
    return EmailAnalyzer([])


# ============================================================================
# Rule Manager Fixtures
# ============================================================================

@pytest.fixture
def temp_rules_file(tmp_path):
    """Create a temporary rules file path."""
    return str(tmp_path / "test_rules.json")


@pytest.fixture
def rule_manager(mock_gmail_service, temp_rules_file):
    """Create a RuleManager with mocked service."""
    return RuleManager(mock_gmail_service, rules_file=temp_rules_file)


@pytest.fixture
def rule_manager_with_rules(rule_manager):
    """Create a RuleManager with some existing rules."""
    rule_manager.create_rule(RuleFactory.create(
        name="Archive LinkedIn",
        from_email="linkedin.com",
        archive=True
    ))
    rule_manager.create_rule(RuleFactory.create(
        name="Label Shopping",
        from_email="amazon.com",
        add_label="Shopping"
    ))
    return rule_manager


# ============================================================================
# Flask Test Client Fixtures
# ============================================================================

@pytest.fixture
def app():
    """Create a Flask test app."""
    from web.app import app as flask_app
    flask_app.config['TESTING'] = True
    flask_app.config['DEBUG'] = False
    return flask_app


@pytest.fixture
def client(app):
    """Create a Flask test client."""
    return app.test_client()


@pytest.fixture
def mock_get_client(mock_gmail_service, monkeypatch):
    """Mock the get_client function in the web app."""
    mock_client = GmailClient(mock_gmail_service, dry_run=True)

    def _get_client():
        return mock_client

    monkeypatch.setattr('web.app.get_client', _get_client)
    return mock_client


@pytest.fixture
def mock_get_rules(mock_gmail_service, temp_rules_file, monkeypatch):
    """Mock the get_rules function in the web app."""
    mock_rules = RuleManager(mock_gmail_service, rules_file=temp_rules_file)

    def _get_rules():
        return mock_rules

    monkeypatch.setattr('web.app.get_rules', _get_rules)
    return mock_rules


# ============================================================================
# Cache and Rate Limit Fixtures
# ============================================================================

@pytest.fixture
def fresh_cache():
    """Get a fresh cache instance for testing."""
    from web.cache import SimpleCache
    return SimpleCache()


@pytest.fixture
def fresh_rate_limiter():
    """Get a fresh rate limiter instance for testing."""
    from web.rate_limit import RateLimiter
    return RateLimiter()


# ============================================================================
# Helper Fixtures
# ============================================================================

@pytest.fixture
def freeze_time():
    """Context manager to freeze time for testing."""
    import time
    original_time = time.time
    frozen_time = [original_time()]

    def get_frozen_time():
        return frozen_time[0]

    def advance_time(seconds):
        frozen_time[0] += seconds

    class FrozenTime:
        def __init__(self):
            self.advance = advance_time

        def __enter__(self):
            time.time = get_frozen_time
            return self

        def __exit__(self, *args):
            time.time = original_time

    return FrozenTime()

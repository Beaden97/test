"""
Tests for the EmailAnalyzer module.

Tests email analysis, sender statistics, newsletter detection,
and cleanup suggestions.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from gmail_cleanup.analyzer import EmailAnalyzer, SenderStats, CleanupSuggestion
from gmail_cleanup.client import Email
from conftest import EmailFactory


class TestSenderStats:
    """Tests for SenderStats dataclass."""

    def test_size_mb_property(self):
        """Test size_mb calculation."""
        stats = SenderStats(
            email="test@example.com",
            name="Test",
            total_size_bytes=1024 * 1024 * 5  # 5 MB
        )
        assert stats.size_mb == 5.0

    def test_size_mb_zero(self):
        """Test size_mb with zero bytes."""
        stats = SenderStats(email="test@example.com", name="Test")
        assert stats.size_mb == 0.0

    def test_str_representation(self):
        """Test string representation."""
        stats = SenderStats(
            email="test@example.com",
            name="Test User",
            total_count=10,
            total_size_bytes=1024 * 1024 * 2  # 2 MB
        )
        result = str(stats)
        assert "Test User" in result
        assert "test@example.com" in result
        assert "10 emails" in result
        assert "2.0 MB" in result


class TestCleanupSuggestion:
    """Tests for CleanupSuggestion dataclass."""

    def test_str_representation(self):
        """Test string representation."""
        suggestion = CleanupSuggestion(
            category="old_newsletters",
            description="Old newsletters from LinkedIn",
            email_ids=["id1", "id2", "id3"],
            estimated_space_mb=1.5,
            priority=2,
            action="archive"
        )
        result = str(suggestion)
        assert "[2]" in result  # Priority
        assert "Old newsletters from LinkedIn" in result
        assert "3 emails" in result
        assert "1.5 MB" in result


class TestEmailAnalyzerBasics:
    """Basic tests for EmailAnalyzer."""

    def test_init_with_emails(self, sample_emails):
        """Test initialization with email list."""
        analyzer = EmailAnalyzer(sample_emails)
        assert analyzer.emails == sample_emails
        assert analyzer._analyzed is False

    def test_init_empty(self):
        """Test initialization with empty list."""
        analyzer = EmailAnalyzer([])
        assert analyzer.emails == []
        assert analyzer._analyzed is False

    def test_analyze_basic(self, email_analyzer):
        """Test basic analysis returns expected keys."""
        result = email_analyzer.analyze()

        assert 'total_emails' in result
        assert 'total_size_mb' in result
        assert 'unread_count' in result
        assert 'sender_count' in result
        assert 'date_range' in result

    def test_analyze_counts(self, sample_emails):
        """Test that analysis counts are correct."""
        analyzer = EmailAnalyzer(sample_emails)
        result = analyzer.analyze()

        assert result['total_emails'] == 4
        assert result['unread_count'] == 2  # Alice and Bob unread
        assert result['sender_count'] == 3  # Alice, Bob, Newsletter

    def test_analyze_sets_analyzed_flag(self, email_analyzer):
        """Test that analyze sets the _analyzed flag."""
        assert email_analyzer._analyzed is False
        email_analyzer.analyze()
        assert email_analyzer._analyzed is True

    def test_analyze_empty_list(self, empty_analyzer):
        """Test analysis with empty email list."""
        result = empty_analyzer.analyze()

        assert result['total_emails'] == 0
        assert result['total_size_mb'] == 0
        assert result['unread_count'] == 0
        assert result['sender_count'] == 0
        assert result['date_range']['oldest'] is None
        assert result['date_range']['newest'] is None


class TestEmailAnalyzerDateRange:
    """Tests for date range calculations."""

    def test_date_range_with_emails(self):
        """Test date range calculation."""
        EmailFactory.reset_counter()
        now = datetime.now(timezone.utc)
        emails = [
            EmailFactory.create(date=now - timedelta(days=10)),
            EmailFactory.create(date=now - timedelta(days=5)),
            EmailFactory.create(date=now - timedelta(days=1)),
        ]
        analyzer = EmailAnalyzer(emails)
        result = analyzer.analyze()

        # Oldest should be 10 days ago, newest 1 day ago
        assert result['date_range']['oldest'] == emails[0].date
        assert result['date_range']['newest'] == emails[2].date

    def test_date_range_single_email(self):
        """Test date range with single email."""
        email = EmailFactory.create()
        analyzer = EmailAnalyzer([email])
        result = analyzer.analyze()

        assert result['date_range']['oldest'] == email.date
        assert result['date_range']['newest'] == email.date


class TestSenderAnalysis:
    """Tests for sender-related analysis."""

    def test_get_top_senders(self, sample_emails):
        """Test getting top senders by email count."""
        analyzer = EmailAnalyzer(sample_emails)
        top_senders = analyzer.get_top_senders(limit=10)

        # Alice has 2 emails, should be first
        assert len(top_senders) >= 1
        assert top_senders[0].email == "alice@company.com"
        assert top_senders[0].total_count == 2

    def test_get_top_senders_auto_analyzes(self, sample_emails):
        """Test that get_top_senders triggers analysis if needed."""
        analyzer = EmailAnalyzer(sample_emails)
        assert analyzer._analyzed is False

        analyzer.get_top_senders()
        assert analyzer._analyzed is True

    def test_get_top_senders_with_limit(self):
        """Test top senders with limit."""
        EmailFactory.reset_counter()
        # Create emails from 5 different senders
        emails = [
            EmailFactory.create(sender_email=f"sender{i}@example.com")
            for i in range(5)
        ]
        analyzer = EmailAnalyzer(emails)

        top_2 = analyzer.get_top_senders(limit=2)
        assert len(top_2) == 2

    def test_get_largest_senders(self):
        """Test getting senders by total size."""
        EmailFactory.reset_counter()
        emails = [
            EmailFactory.create(sender_email="small@example.com", size_bytes=1000),
            EmailFactory.create(sender_email="large@example.com", size_bytes=1000000),
        ]
        analyzer = EmailAnalyzer(emails)

        largest = analyzer.get_largest_senders(limit=10)
        assert largest[0].email == "large@example.com"

    def test_get_sender_stats(self, sample_emails):
        """Test getting stats for specific sender."""
        analyzer = EmailAnalyzer(sample_emails)
        stats = analyzer.get_sender_stats("alice@company.com")

        assert stats is not None
        assert stats.email == "alice@company.com"
        assert stats.total_count == 2

    def test_get_sender_stats_case_insensitive(self, sample_emails):
        """Test sender lookup is case insensitive."""
        analyzer = EmailAnalyzer(sample_emails)
        stats = analyzer.get_sender_stats("ALICE@COMPANY.COM")

        assert stats is not None
        assert stats.total_count == 2

    def test_get_sender_stats_not_found(self, sample_emails):
        """Test getting stats for nonexistent sender."""
        analyzer = EmailAnalyzer(sample_emails)
        stats = analyzer.get_sender_stats("nobody@example.com")

        assert stats is None

    def test_sender_stats_sample_subjects(self):
        """Test that sample subjects are collected (max 3)."""
        EmailFactory.reset_counter()
        emails = [
            EmailFactory.create(
                sender_email="sender@example.com",
                subject=f"Subject {i}"
            )
            for i in range(5)
        ]
        analyzer = EmailAnalyzer(emails)
        stats = analyzer.get_sender_stats("sender@example.com")

        assert len(stats.sample_subjects) == 3  # Limited to 3


class TestNewsletterDetection:
    """Tests for newsletter/marketing email detection."""

    def test_find_newsletters_by_sender_pattern(self):
        """Test finding newsletters by sender email patterns."""
        EmailFactory.reset_counter()
        emails = [
            EmailFactory.create(sender_email="noreply@company.com"),
            EmailFactory.create(sender_email="normal@example.com"),
            EmailFactory.create(sender_email="marketing@promo.com"),
        ]
        analyzer = EmailAnalyzer(emails)
        newsletters = analyzer.find_newsletters()

        newsletter_emails = [n.email for n in newsletters]
        assert "noreply@company.com" in newsletter_emails
        assert "marketing@promo.com" in newsletter_emails

    def test_find_newsletters_by_subject_pattern(self):
        """Test finding newsletters by subject patterns."""
        EmailFactory.reset_counter()
        # Need 5+ emails from same sender to trigger subject check
        emails = [
            EmailFactory.create(
                sender_email="sender@example.com",
                subject="Weekly Digest"
            )
            for _ in range(6)
        ]
        analyzer = EmailAnalyzer(emails)
        newsletters = analyzer.find_newsletters()

        assert len(newsletters) == 1
        assert newsletters[0].email == "sender@example.com"

    def test_find_newsletters_unsubscribe_pattern(self):
        """Test newsletter detection with unsubscribe in subject."""
        EmailFactory.reset_counter()
        emails = [
            EmailFactory.create(
                sender_email="updates@company.com",
                subject="Update - Click to unsubscribe"
            )
            for _ in range(6)
        ]
        analyzer = EmailAnalyzer(emails)
        newsletters = analyzer.find_newsletters()

        assert len(newsletters) >= 1

    def test_find_newsletters_sorted_by_count(self):
        """Test newsletters are sorted by email count."""
        EmailFactory.reset_counter()
        emails = []
        # 3 emails from newsletter1
        for _ in range(3):
            emails.append(EmailFactory.create(sender_email="noreply@newsletter1.com"))
        # 10 emails from newsletter2
        for _ in range(10):
            emails.append(EmailFactory.create(sender_email="noreply@newsletter2.com"))

        analyzer = EmailAnalyzer(emails)
        newsletters = analyzer.find_newsletters()

        assert newsletters[0].email == "noreply@newsletter2.com"

    def test_find_newsletters_empty(self):
        """Test finding newsletters when none exist."""
        EmailFactory.reset_counter()
        emails = [
            EmailFactory.create(sender_email="friend@personal.com"),
            EmailFactory.create(sender_email="colleague@work.com"),
        ]
        analyzer = EmailAnalyzer(emails)
        newsletters = analyzer.find_newsletters()

        assert newsletters == []


class TestOldEmailDetection:
    """Tests for finding old emails."""

    def test_find_old_emails(self):
        """Test finding emails older than threshold."""
        EmailFactory.reset_counter()
        now = datetime.now(timezone.utc)
        emails = [
            EmailFactory.create(date=now - timedelta(days=400)),  # Old
            EmailFactory.create(date=now - timedelta(days=100)),  # Recent
            EmailFactory.create(date=now - timedelta(days=500)),  # Very old
        ]
        analyzer = EmailAnalyzer(emails)
        old_emails = analyzer.find_old_emails(days=365)

        assert len(old_emails) == 2

    def test_find_old_emails_custom_threshold(self):
        """Test old email detection with custom threshold."""
        EmailFactory.reset_counter()
        now = datetime.now(timezone.utc)
        emails = [
            EmailFactory.create(date=now - timedelta(days=40)),
            EmailFactory.create(date=now - timedelta(days=20)),
        ]
        analyzer = EmailAnalyzer(emails)

        old_30_days = analyzer.find_old_emails(days=30)
        assert len(old_30_days) == 1

        old_50_days = analyzer.find_old_emails(days=50)
        assert len(old_50_days) == 0

    def test_find_old_emails_empty_list(self, empty_analyzer):
        """Test finding old emails with empty list."""
        result = empty_analyzer.find_old_emails(days=365)
        assert result == []

    def test_find_old_emails_none_old(self):
        """Test when no emails are old enough."""
        EmailFactory.reset_counter()
        now = datetime.now(timezone.utc)
        emails = [
            EmailFactory.create(date=now - timedelta(days=1)),
            EmailFactory.create(date=now - timedelta(days=10)),
        ]
        analyzer = EmailAnalyzer(emails)
        old_emails = analyzer.find_old_emails(days=365)

        assert old_emails == []


class TestLargeEmailDetection:
    """Tests for finding large emails."""

    def test_find_large_emails(self):
        """Test finding emails larger than threshold."""
        EmailFactory.reset_counter()
        emails = [
            EmailFactory.create(size_bytes=1024),  # 1 KB
            EmailFactory.create(size_bytes=10 * 1024 * 1024),  # 10 MB
            EmailFactory.create(size_bytes=20 * 1024 * 1024),  # 20 MB
        ]
        analyzer = EmailAnalyzer(emails)
        large_emails = analyzer.find_large_emails(min_size_mb=5.0)

        assert len(large_emails) == 2

    def test_find_large_emails_sorted(self):
        """Test large emails are sorted by size descending."""
        EmailFactory.reset_counter()
        emails = [
            EmailFactory.create(size_bytes=10 * 1024 * 1024),  # 10 MB
            EmailFactory.create(size_bytes=20 * 1024 * 1024),  # 20 MB
            EmailFactory.create(size_bytes=15 * 1024 * 1024),  # 15 MB
        ]
        analyzer = EmailAnalyzer(emails)
        large_emails = analyzer.find_large_emails(min_size_mb=5.0)

        assert large_emails[0].size_bytes == 20 * 1024 * 1024
        assert large_emails[1].size_bytes == 15 * 1024 * 1024
        assert large_emails[2].size_bytes == 10 * 1024 * 1024

    def test_find_large_emails_custom_threshold(self):
        """Test with custom size threshold."""
        EmailFactory.reset_counter()
        emails = [
            EmailFactory.create(size_bytes=100 * 1024 * 1024),  # 100 MB
        ]
        analyzer = EmailAnalyzer(emails)

        result_50mb = analyzer.find_large_emails(min_size_mb=50.0)
        assert len(result_50mb) == 1

        result_200mb = analyzer.find_large_emails(min_size_mb=200.0)
        assert len(result_200mb) == 0

    def test_find_large_emails_none_large(self):
        """Test when no emails are large enough."""
        EmailFactory.reset_counter()
        emails = [
            EmailFactory.create(size_bytes=1024),
            EmailFactory.create(size_bytes=2048),
        ]
        analyzer = EmailAnalyzer(emails)
        large_emails = analyzer.find_large_emails(min_size_mb=5.0)

        assert large_emails == []


class TestCleanupSuggestions:
    """Tests for cleanup suggestions."""

    def test_get_cleanup_suggestions_structure(self):
        """Test that suggestions have correct structure."""
        EmailFactory.reset_counter()
        now = datetime.now(timezone.utc)
        emails = [
            EmailFactory.create_large_email(size_mb=15),  # Large email
            EmailFactory.create_old_email(days_old=800),  # Very old
        ]
        analyzer = EmailAnalyzer(emails)
        suggestions = analyzer.get_cleanup_suggestions()

        for suggestion in suggestions:
            assert isinstance(suggestion, CleanupSuggestion)
            assert suggestion.category
            assert suggestion.description
            assert isinstance(suggestion.email_ids, list)
            assert suggestion.priority in [1, 2, 3]
            assert suggestion.action

    def test_get_cleanup_suggestions_sorted_by_priority(self):
        """Test suggestions are sorted by priority."""
        EmailFactory.reset_counter()
        now = datetime.now(timezone.utc)
        emails = [
            EmailFactory.create_large_email(size_mb=15),  # Priority 1
            EmailFactory.create_old_email(days_old=800),  # Priority 3
        ]
        analyzer = EmailAnalyzer(emails)
        suggestions = analyzer.get_cleanup_suggestions()

        if len(suggestions) > 1:
            for i in range(len(suggestions) - 1):
                assert suggestions[i].priority <= suggestions[i + 1].priority

    def test_get_cleanup_suggestions_large_emails(self):
        """Test suggestion for large emails."""
        EmailFactory.reset_counter()
        emails = [
            EmailFactory.create_large_email(size_mb=15),
            EmailFactory.create_large_email(size_mb=20),
        ]
        analyzer = EmailAnalyzer(emails)
        suggestions = analyzer.get_cleanup_suggestions()

        large_suggestion = next(
            (s for s in suggestions if s.category == "large_emails"),
            None
        )
        assert large_suggestion is not None
        assert len(large_suggestion.email_ids) == 2
        assert large_suggestion.priority == 1

    def test_get_cleanup_suggestions_very_old(self):
        """Test suggestion for very old emails."""
        EmailFactory.reset_counter()
        emails = [
            EmailFactory.create_old_email(days_old=800),
            EmailFactory.create_old_email(days_old=900),
        ]
        analyzer = EmailAnalyzer(emails)
        suggestions = analyzer.get_cleanup_suggestions()

        old_suggestion = next(
            (s for s in suggestions if s.category == "very_old"),
            None
        )
        assert old_suggestion is not None
        assert len(old_suggestion.email_ids) == 2
        assert old_suggestion.action == "archive"

    def test_get_cleanup_suggestions_high_volume_sender(self):
        """Test suggestion for high-volume senders."""
        EmailFactory.reset_counter()
        # Create 60 emails from same sender
        emails = [
            EmailFactory.create(sender_email="spammer@example.com")
            for _ in range(60)
        ]
        analyzer = EmailAnalyzer(emails)
        suggestions = analyzer.get_cleanup_suggestions()

        high_volume = next(
            (s for s in suggestions if s.category == "high_volume"),
            None
        )
        assert high_volume is not None
        assert "60 emails" in high_volume.description

    def test_get_cleanup_suggestions_auto_analyzes(self):
        """Test that getting suggestions triggers analysis."""
        EmailFactory.reset_counter()
        emails = [EmailFactory.create()]
        analyzer = EmailAnalyzer(emails)

        assert analyzer._analyzed is False
        analyzer.get_cleanup_suggestions()
        assert analyzer._analyzed is True


class TestGroupByDomain:
    """Tests for grouping senders by domain."""

    def test_group_by_domain(self):
        """Test grouping senders by email domain."""
        EmailFactory.reset_counter()
        emails = [
            EmailFactory.create(sender_email="alice@company.com"),
            EmailFactory.create(sender_email="bob@company.com"),
            EmailFactory.create(sender_email="carol@other.org"),
        ]
        analyzer = EmailAnalyzer(emails)
        domains = analyzer.group_by_domain()

        assert "company.com" in domains
        assert "other.org" in domains
        assert len(domains["company.com"]) == 2
        assert len(domains["other.org"]) == 1

    def test_group_by_domain_case_insensitive(self):
        """Test domain grouping is case insensitive."""
        EmailFactory.reset_counter()
        emails = [
            EmailFactory.create(sender_email="alice@Company.Com"),
            EmailFactory.create(sender_email="bob@COMPANY.COM"),
        ]
        analyzer = EmailAnalyzer(emails)
        domains = analyzer.group_by_domain()

        assert "company.com" in domains
        assert len(domains["company.com"]) == 2

    def test_group_by_domain_sorted_by_count(self):
        """Test senders within domain are sorted by count."""
        EmailFactory.reset_counter()
        emails = [
            EmailFactory.create(sender_email="alice@company.com"),
            EmailFactory.create(sender_email="bob@company.com"),
            EmailFactory.create(sender_email="bob@company.com"),  # Bob has 2
        ]
        analyzer = EmailAnalyzer(emails)
        domains = analyzer.group_by_domain()

        senders = domains["company.com"]
        assert senders[0].email == "bob@company.com"  # First (higher count)

    def test_group_by_domain_auto_analyzes(self):
        """Test that group_by_domain triggers analysis."""
        EmailFactory.reset_counter()
        emails = [EmailFactory.create()]
        analyzer = EmailAnalyzer(emails)

        assert analyzer._analyzed is False
        analyzer.group_by_domain()
        assert analyzer._analyzed is True

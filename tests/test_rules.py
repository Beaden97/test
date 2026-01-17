"""
Tests for the RuleManager module.

Tests rule creation, deletion, syncing to Gmail filters,
and applying rules to existing emails.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from gmail_cleanup.rules import Rule, RuleManager, quick_rule
from conftest import RuleFactory


class TestRuleDataclass:
    """Tests for the Rule dataclass."""

    def test_rule_creation(self):
        """Test creating a Rule object."""
        rule = Rule(
            name="Test Rule",
            from_email="test@example.com",
            archive=True,
            add_label="TestLabel"
        )
        assert rule.name == "Test Rule"
        assert rule.from_email == "test@example.com"
        assert rule.archive is True
        assert rule.add_label == "TestLabel"

    def test_rule_default_values(self):
        """Test Rule default values."""
        rule = Rule(name="Minimal Rule")

        assert rule.from_email is None
        assert rule.to_email is None
        assert rule.subject_contains is None
        assert rule.has_words is None
        assert rule.add_label is None
        assert rule.remove_label is None
        assert rule.archive is False
        assert rule.mark_read is False
        assert rule.star is False
        assert rule.never_spam is False
        assert rule.forward_to is None
        assert rule.gmail_filter_id is None

    def test_rule_str_with_conditions(self):
        """Test Rule string representation with conditions."""
        rule = Rule(
            name="LinkedIn",
            from_email="linkedin.com",
            archive=True,
            add_label="Networking"
        )
        result = str(rule)

        assert "LinkedIn" in result
        assert "from:linkedin.com" in result
        assert "Archive" in result
        assert "Networking" in result

    def test_rule_str_with_subject(self):
        """Test Rule string with subject condition."""
        rule = Rule(
            name="Alerts",
            subject_contains="URGENT",
            star=True
        )
        result = str(rule)

        assert "subject:URGENT" in result

    def test_rule_str_with_multiple_conditions(self):
        """Test Rule string with multiple conditions."""
        rule = Rule(
            name="Complex Rule",
            from_email="company.com",
            subject_contains="Newsletter",
            has_words="unsubscribe"
        )
        result = str(rule)

        assert "from:company.com" in result
        assert "subject:Newsletter" in result
        assert "has:unsubscribe" in result
        assert "AND" in result


class TestRuleManagerInit:
    """Tests for RuleManager initialization."""

    def test_init_creates_empty_rules(self, mock_gmail_service, temp_rules_file):
        """Test initialization with no existing rules file."""
        manager = RuleManager(mock_gmail_service, rules_file=temp_rules_file)

        assert manager.rules == []
        assert manager.service == mock_gmail_service

    def test_init_loads_existing_rules(self, mock_gmail_service, temp_rules_file):
        """Test initialization loads existing rules file."""
        # Create rules file first
        rules_data = {
            'rules': [
                {'name': 'Rule 1', 'from_email': 'test@example.com', 'archive': True}
            ]
        }
        Path(temp_rules_file).parent.mkdir(parents=True, exist_ok=True)
        with open(temp_rules_file, 'w') as f:
            json.dump(rules_data, f)

        manager = RuleManager(mock_gmail_service, rules_file=temp_rules_file)

        assert len(manager.rules) == 1
        assert manager.rules[0].name == 'Rule 1'

    def test_init_handles_corrupt_file(self, mock_gmail_service, temp_rules_file, capsys):
        """Test initialization handles corrupt rules file."""
        Path(temp_rules_file).parent.mkdir(parents=True, exist_ok=True)
        with open(temp_rules_file, 'w') as f:
            f.write("not valid json")

        manager = RuleManager(mock_gmail_service, rules_file=temp_rules_file)

        assert manager.rules == []
        captured = capsys.readouterr()
        assert "Couldn't load rules" in captured.out


class TestRuleManagerCreateRule:
    """Tests for rule creation."""

    def test_create_rule(self, rule_manager):
        """Test creating a new rule."""
        rule = RuleFactory.create(name="New Rule", from_email="example.com")
        created = rule_manager.create_rule(rule)

        assert created == rule
        assert len(rule_manager.rules) == 1
        assert rule_manager.rules[0].name == "New Rule"

    def test_create_rule_saves_to_file(self, rule_manager, temp_rules_file):
        """Test that creating a rule saves to file."""
        rule = RuleFactory.create(name="Saved Rule")
        rule_manager.create_rule(rule)

        # Read file and verify
        with open(temp_rules_file) as f:
            data = json.load(f)

        assert len(data['rules']) == 1
        assert data['rules'][0]['name'] == "Saved Rule"

    def test_create_multiple_rules(self, rule_manager):
        """Test creating multiple rules."""
        rule_manager.create_rule(RuleFactory.create(name="Rule 1"))
        rule_manager.create_rule(RuleFactory.create(name="Rule 2"))
        rule_manager.create_rule(RuleFactory.create(name="Rule 3"))

        assert len(rule_manager.rules) == 3


class TestRuleManagerDeleteRule:
    """Tests for rule deletion."""

    def test_delete_rule(self, rule_manager_with_rules):
        """Test deleting an existing rule."""
        initial_count = len(rule_manager_with_rules.rules)
        result = rule_manager_with_rules.delete_rule("Archive LinkedIn")

        assert result is True
        assert len(rule_manager_with_rules.rules) == initial_count - 1

    def test_delete_rule_not_found(self, rule_manager, capsys):
        """Test deleting a nonexistent rule."""
        result = rule_manager.delete_rule("Nonexistent Rule")

        assert result is False
        captured = capsys.readouterr()
        assert "not found" in captured.out

    def test_delete_synced_rule(self, rule_manager, mock_gmail_service):
        """Test deleting a rule that's synced to Gmail."""
        # Create a synced rule
        rule = RuleFactory.create(
            name="Synced Rule",
            from_email="test.com",
            gmail_filter_id="filter123"
        )
        rule_manager.rules.append(rule)

        mock_gmail_service.users().settings().filters().delete.return_value.execute.return_value = {}

        result = rule_manager.delete_rule("Synced Rule")

        assert result is True
        mock_gmail_service.users().settings().filters().delete.assert_called_once()

    def test_delete_synced_rule_api_error(self, rule_manager, mock_gmail_service, capsys):
        """Test deleting synced rule when API fails."""
        rule = RuleFactory.create(
            name="Synced Rule",
            from_email="test.com",
            gmail_filter_id="filter123"
        )
        rule_manager.rules.append(rule)

        mock_gmail_service.users().settings().filters().delete.return_value.execute.side_effect = Exception("API Error")

        result = rule_manager.delete_rule("Synced Rule")

        # Rule should still be deleted locally
        assert result is True
        captured = capsys.readouterr()
        assert "Couldn't remove Gmail filter" in captured.out


class TestRuleManagerListRules:
    """Tests for listing rules."""

    def test_list_rules_empty(self, rule_manager):
        """Test listing when no rules exist."""
        rules = rule_manager.list_rules()
        assert rules == []

    def test_list_rules(self, rule_manager_with_rules):
        """Test listing existing rules."""
        rules = rule_manager_with_rules.list_rules()

        assert len(rules) == 2
        names = [r.name for r in rules]
        assert "Archive LinkedIn" in names
        assert "Label Shopping" in names


class TestRuleManagerSyncToGmail:
    """Tests for syncing rules to Gmail filters."""

    def test_sync_to_gmail_basic(self, rule_manager, mock_gmail_service):
        """Test syncing a basic rule to Gmail."""
        mock_gmail_service.users().settings().filters().create.return_value.execute.return_value = {
            'id': 'filter123'
        }

        rule = RuleFactory.create(
            name="Test Rule",
            from_email="example.com",
            archive=True
        )
        rule_manager.rules.append(rule)

        result = rule_manager.sync_to_gmail(rule)

        assert result is True
        assert rule.gmail_filter_id == 'filter123'
        mock_gmail_service.users().settings().filters().create.assert_called_once()

    def test_sync_to_gmail_no_criteria(self, rule_manager, capsys):
        """Test syncing rule with no conditions."""
        rule = RuleFactory.create(name="Empty Rule")

        result = rule_manager.sync_to_gmail(rule)

        assert result is False
        captured = capsys.readouterr()
        assert "at least one condition" in captured.out

    def test_sync_to_gmail_no_action(self, rule_manager, capsys):
        """Test syncing rule with no actions."""
        rule = RuleFactory.create(
            name="No Action Rule",
            from_email="example.com"
            # No actions specified
        )

        result = rule_manager.sync_to_gmail(rule)

        assert result is False
        captured = capsys.readouterr()
        assert "at least one action" in captured.out

    def test_sync_to_gmail_with_label(self, rule_manager, mock_gmail_service):
        """Test syncing rule that adds a label."""
        # Mock label lookup - not found, then create
        mock_gmail_service.users().labels().list.return_value.execute.return_value = {
            'labels': []
        }
        mock_gmail_service.users().labels().create.return_value.execute.return_value = {
            'id': 'Label_123',
            'name': 'MyLabel'
        }
        mock_gmail_service.users().settings().filters().create.return_value.execute.return_value = {
            'id': 'filter123'
        }

        rule = RuleFactory.create(
            name="Label Rule",
            from_email="example.com",
            add_label="MyLabel"
        )

        result = rule_manager.sync_to_gmail(rule)

        assert result is True
        mock_gmail_service.users().labels().create.assert_called()

    def test_sync_to_gmail_api_error(self, rule_manager, mock_gmail_service, capsys):
        """Test syncing when Gmail API fails."""
        mock_gmail_service.users().settings().filters().create.return_value.execute.side_effect = Exception("API Error")

        rule = RuleFactory.create(
            name="Failing Rule",
            from_email="example.com",
            archive=True
        )

        result = rule_manager.sync_to_gmail(rule)

        assert result is False
        captured = capsys.readouterr()
        assert "Couldn't create Gmail filter" in captured.out

    def test_sync_to_gmail_mark_read(self, rule_manager, mock_gmail_service):
        """Test syncing rule that marks as read."""
        mock_gmail_service.users().settings().filters().create.return_value.execute.return_value = {
            'id': 'filter123'
        }

        rule = RuleFactory.create(
            name="Mark Read Rule",
            from_email="example.com",
            mark_read=True
        )

        rule_manager.sync_to_gmail(rule)

        call_args = mock_gmail_service.users().settings().filters().create.call_args
        body = call_args[1]['body']
        assert 'UNREAD' in body['action'].get('removeLabelIds', [])

    def test_sync_to_gmail_star(self, rule_manager, mock_gmail_service):
        """Test syncing rule that stars emails."""
        mock_gmail_service.users().settings().filters().create.return_value.execute.return_value = {
            'id': 'filter123'
        }

        rule = RuleFactory.create(
            name="Star Rule",
            from_email="important@example.com",
            star=True
        )

        rule_manager.sync_to_gmail(rule)

        call_args = mock_gmail_service.users().settings().filters().create.call_args
        body = call_args[1]['body']
        assert 'STARRED' in body['action'].get('addLabelIds', [])


class TestRuleManagerGetGmailFilters:
    """Tests for getting existing Gmail filters."""

    def test_get_gmail_filters(self, rule_manager, mock_gmail_service):
        """Test getting Gmail filters."""
        mock_gmail_service.users().settings().filters().list.return_value.execute.return_value = {
            'filter': [
                {'id': 'filter1', 'criteria': {'from': 'test.com'}},
                {'id': 'filter2', 'criteria': {'subject': 'Alert'}},
            ]
        }

        filters = rule_manager.get_gmail_filters()

        assert len(filters) == 2

    def test_get_gmail_filters_empty(self, rule_manager, mock_gmail_service):
        """Test getting filters when none exist."""
        mock_gmail_service.users().settings().filters().list.return_value.execute.return_value = {
            'filter': []
        }

        filters = rule_manager.get_gmail_filters()
        assert filters == []

    def test_get_gmail_filters_api_error(self, rule_manager, mock_gmail_service, capsys):
        """Test getting filters when API fails."""
        mock_gmail_service.users().settings().filters().list.return_value.execute.side_effect = Exception("API Error")

        filters = rule_manager.get_gmail_filters()

        assert filters == []
        captured = capsys.readouterr()
        assert "Couldn't fetch Gmail filters" in captured.out


class TestRuleManagerApplyToExisting:
    """Tests for applying rules to existing emails."""

    def test_apply_rule_dry_run(self, rule_manager, mock_gmail_service, capsys):
        """Test applying rule in dry run mode."""
        mock_gmail_service.users().messages().list.return_value.execute.return_value = {
            'messages': [{'id': 'msg1'}, {'id': 'msg2'}]
        }

        rule = RuleFactory.create(
            name="Test Rule",
            from_email="example.com",
            archive=True
        )

        count = rule_manager.apply_rule_to_existing(rule, dry_run=True)

        assert count == 2
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out

    def test_apply_rule_live(self, rule_manager, mock_gmail_service):
        """Test applying rule in live mode."""
        mock_gmail_service.users().messages().list.return_value.execute.return_value = {
            'messages': [{'id': 'msg1'}, {'id': 'msg2'}]
        }
        mock_gmail_service.users().messages().modify.return_value.execute.return_value = {}

        rule = RuleFactory.create(
            name="Test Rule",
            from_email="example.com",
            archive=True
        )

        count = rule_manager.apply_rule_to_existing(rule, dry_run=False)

        assert count == 2

    def test_apply_rule_no_matches(self, rule_manager, mock_gmail_service, capsys):
        """Test applying rule when no emails match."""
        mock_gmail_service.users().messages().list.return_value.execute.return_value = {
            'messages': []
        }

        rule = RuleFactory.create(
            name="Test Rule",
            from_email="nobody@example.com"
        )

        count = rule_manager.apply_rule_to_existing(rule, dry_run=False)

        assert count == 0
        captured = capsys.readouterr()
        assert "No emails match" in captured.out

    def test_apply_rule_no_conditions(self, rule_manager, capsys):
        """Test applying rule with no conditions."""
        rule = RuleFactory.create(name="Empty Rule")

        count = rule_manager.apply_rule_to_existing(rule, dry_run=False)

        assert count == 0
        captured = capsys.readouterr()
        assert "at least one condition" in captured.out

    def test_apply_rule_with_label(self, rule_manager, mock_gmail_service):
        """Test applying rule that adds a label."""
        mock_gmail_service.users().messages().list.return_value.execute.return_value = {
            'messages': [{'id': 'msg1'}]
        }
        mock_gmail_service.users().labels().list.return_value.execute.return_value = {
            'labels': [{'id': 'Label_123', 'name': 'MyLabel'}]
        }
        mock_gmail_service.users().messages().modify.return_value.execute.return_value = {}

        rule = RuleFactory.create(
            name="Label Rule",
            from_email="example.com",
            add_label="MyLabel"
        )

        count = rule_manager.apply_rule_to_existing(rule, dry_run=False)

        assert count == 1

    def test_apply_rule_api_error(self, rule_manager, mock_gmail_service, capsys):
        """Test applying rule when search fails."""
        mock_gmail_service.users().messages().list.return_value.execute.side_effect = Exception("API Error")

        rule = RuleFactory.create(
            name="Test Rule",
            from_email="example.com",
            archive=True
        )

        count = rule_manager.apply_rule_to_existing(rule, dry_run=False)

        assert count == 0
        captured = capsys.readouterr()
        assert "Error searching" in captured.out

    def test_apply_rule_max_emails(self, rule_manager, mock_gmail_service):
        """Test max_emails limit is respected."""
        mock_gmail_service.users().messages().list.return_value.execute.return_value = {
            'messages': [{'id': f'msg{i}'} for i in range(100)]
        }
        mock_gmail_service.users().messages().modify.return_value.execute.return_value = {}

        rule = RuleFactory.create(
            name="Test Rule",
            from_email="example.com",
            archive=True
        )

        rule_manager.apply_rule_to_existing(rule, max_emails=50, dry_run=False)

        call_args = mock_gmail_service.users().messages().list.call_args
        assert call_args[1]['maxResults'] == 50


class TestQuickRule:
    """Tests for the quick_rule helper function."""

    def test_quick_rule_archive(self):
        """Test creating archive rule."""
        rule = quick_rule("LinkedIn", "linkedin.com", "archive")

        assert rule.name == "LinkedIn"
        assert rule.from_email == "linkedin.com"
        assert rule.archive is True
        assert rule.add_label is None

    def test_quick_rule_label(self):
        """Test creating label rule."""
        rule = quick_rule("Amazon", "amazon.com", "label", "Shopping")

        assert rule.name == "Amazon"
        assert rule.from_email == "amazon.com"
        assert rule.archive is False
        assert rule.add_label == "Shopping"

    def test_quick_rule_both(self):
        """Test creating archive+label rule."""
        rule = quick_rule("News", "news.com", "both", "News")

        assert rule.archive is True
        assert rule.add_label == "News"

    def test_quick_rule_read(self):
        """Test creating mark-read rule."""
        rule = quick_rule("Alerts", "alerts.com", "read")

        assert rule.mark_read is True
        assert rule.archive is False

    def test_quick_rule_label_defaults_to_name(self):
        """Test label defaults to rule name when not specified."""
        rule = quick_rule("Shopping", "amazon.com", "label")

        assert rule.add_label == "Shopping"


class TestLabelHelpers:
    """Tests for label helper methods."""

    def test_get_label_id_found(self, rule_manager, mock_gmail_service):
        """Test getting label ID when label exists."""
        mock_gmail_service.users().labels().list.return_value.execute.return_value = {
            'labels': [
                {'id': 'Label_123', 'name': 'MyLabel'},
                {'id': 'Label_456', 'name': 'Other'},
            ]
        }

        label_id = rule_manager._get_label_id("MyLabel")

        assert label_id == 'Label_123'

    def test_get_label_id_not_found(self, rule_manager, mock_gmail_service):
        """Test getting label ID when label doesn't exist."""
        mock_gmail_service.users().labels().list.return_value.execute.return_value = {
            'labels': []
        }

        label_id = rule_manager._get_label_id("NonexistentLabel")

        assert label_id is None

    def test_get_label_id_case_insensitive(self, rule_manager, mock_gmail_service):
        """Test label lookup is case insensitive."""
        mock_gmail_service.users().labels().list.return_value.execute.return_value = {
            'labels': [{'id': 'Label_123', 'name': 'MyLabel'}]
        }

        label_id = rule_manager._get_label_id("mylabel")

        assert label_id == 'Label_123'

    def test_get_label_id_caching(self, rule_manager, mock_gmail_service):
        """Test label ID is cached."""
        mock_gmail_service.users().labels().list.return_value.execute.return_value = {
            'labels': [{'id': 'Label_123', 'name': 'MyLabel'}]
        }

        # First call
        rule_manager._get_label_id("MyLabel")
        # Second call should use cache
        rule_manager._get_label_id("MyLabel")

        # API should only be called once
        assert mock_gmail_service.users().labels().list.call_count == 1

    def test_get_or_create_label_exists(self, rule_manager, mock_gmail_service):
        """Test get_or_create when label exists."""
        mock_gmail_service.users().labels().list.return_value.execute.return_value = {
            'labels': [{'id': 'Label_123', 'name': 'ExistingLabel'}]
        }

        label_id = rule_manager._get_or_create_label("ExistingLabel")

        assert label_id == 'Label_123'
        mock_gmail_service.users().labels().create.assert_not_called()

    def test_get_or_create_label_creates(self, rule_manager, mock_gmail_service):
        """Test get_or_create creates new label."""
        mock_gmail_service.users().labels().list.return_value.execute.return_value = {
            'labels': []
        }
        mock_gmail_service.users().labels().create.return_value.execute.return_value = {
            'id': 'Label_New',
            'name': 'NewLabel'
        }

        label_id = rule_manager._get_or_create_label("NewLabel")

        assert label_id == 'Label_New'
        mock_gmail_service.users().labels().create.assert_called_once()

    def test_get_or_create_label_create_fails(self, rule_manager, mock_gmail_service, capsys):
        """Test get_or_create when create fails."""
        mock_gmail_service.users().labels().list.return_value.execute.return_value = {
            'labels': []
        }
        mock_gmail_service.users().labels().create.return_value.execute.side_effect = Exception("API Error")

        label_id = rule_manager._get_or_create_label("NewLabel")

        assert label_id is None
        captured = capsys.readouterr()
        assert "Couldn't create label" in captured.out

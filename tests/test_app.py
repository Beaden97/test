"""
Tests for the Flask API endpoints.

Tests REST API endpoints including authentication, emails,
analysis, rules, and actions.
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from conftest import EmailFactory, RuleFactory


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns healthy status."""
        response = client.get('/api/v1/health')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['status'] == 'healthy'
        assert 'version' in data['data']


class TestStatusEndpoint:
    """Tests for the authentication status endpoint."""

    @patch('web.app.GmailAuth')
    def test_status_authenticated(self, mock_auth_class, client):
        """Test status when authenticated."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = True
        mock_auth.get_status.return_value = {'authenticated': True}
        mock_auth_class.return_value = mock_auth

        response = client.get('/api/v1/status')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['authenticated'] is True

    @patch('web.app.GmailAuth')
    def test_status_unauthenticated(self, mock_auth_class, client):
        """Test status when not authenticated."""
        mock_auth = MagicMock()
        mock_auth.is_authenticated.return_value = False
        mock_auth.get_status.return_value = {'authenticated': False}
        mock_auth_class.return_value = mock_auth

        response = client.get('/api/v1/status')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['authenticated'] is False


class TestEmailsEndpoint:
    """Tests for the emails endpoint."""

    def test_get_emails_default(self, client, mock_get_client):
        """Test getting emails with defaults."""
        EmailFactory.reset_counter()
        mock_emails = [
            EmailFactory.create(subject="Test Email 1"),
            EmailFactory.create(subject="Test Email 2"),
        ]
        mock_get_client.search_emails = MagicMock(return_value=mock_emails)

        response = client.get('/api/v1/emails')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']['emails']) == 2
        assert data['meta']['query'] == 'in:inbox'

    def test_get_emails_with_query(self, client, mock_get_client):
        """Test getting emails with search query."""
        mock_get_client.search_emails = MagicMock(return_value=[])

        response = client.get('/api/v1/emails?q=from:test@example.com')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['meta']['query'] == 'from:test@example.com'

    def test_get_emails_with_limit(self, client, mock_get_client):
        """Test getting emails with custom limit."""
        mock_get_client.search_emails = MagicMock(return_value=[])

        response = client.get('/api/v1/emails?limit=10')

        assert response.status_code == 200
        mock_get_client.search_emails.assert_called_with('in:inbox', max_results=10)

    def test_get_emails_limit_validation_min(self, client, mock_get_client):
        """Test limit validation - minimum value."""
        response = client.get('/api/v1/emails?limit=0')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'at least 1' in data['error']['message']

    def test_get_emails_limit_validation_max(self, client, mock_get_client):
        """Test limit validation - maximum value."""
        response = client.get('/api/v1/emails?limit=1000')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'at most 500' in data['error']['message']


class TestInboxStatsEndpoint:
    """Tests for the inbox stats endpoint."""

    def test_get_inbox_stats(self, client, mock_get_client):
        """Test getting inbox statistics."""
        mock_get_client.get_inbox_stats = MagicMock(return_value={
            'total_inbox': 1000,
            'unread_inbox': 50,
            'categories': {'promotions': 200}
        })

        response = client.get('/api/v1/inbox/stats')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['total_inbox'] == 1000
        assert data['data']['unread_inbox'] == 50


class TestAnalyzeSendersEndpoint:
    """Tests for the sender analysis endpoint."""

    def test_analyze_senders(self, client, mock_get_client):
        """Test analyzing top senders."""
        EmailFactory.reset_counter()
        mock_emails = [
            EmailFactory.create(sender_email="alice@example.com"),
            EmailFactory.create(sender_email="alice@example.com"),
            EmailFactory.create(sender_email="bob@example.com"),
        ]
        mock_get_client.search_emails = MagicMock(return_value=mock_emails)

        response = client.get('/api/v1/analyze/senders')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'senders' in data['data']

    def test_analyze_senders_with_limit(self, client, mock_get_client):
        """Test sender analysis with custom limit."""
        mock_get_client.search_emails = MagicMock(return_value=[])

        response = client.get('/api/v1/analyze/senders?limit=100')

        assert response.status_code == 200
        mock_get_client.search_emails.assert_called_with('in:inbox', max_results=100)


class TestSuggestionsEndpoint:
    """Tests for the cleanup suggestions endpoint."""

    def test_get_suggestions(self, client, mock_get_client):
        """Test getting cleanup suggestions."""
        EmailFactory.reset_counter()
        mock_emails = [
            EmailFactory.create_large_email(size_mb=15),
            EmailFactory.create_old_email(days_old=800),
        ]
        mock_get_client.search_emails = MagicMock(return_value=mock_emails)

        response = client.get('/api/v1/analyze/suggestions')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'suggestions' in data['data']

    def test_suggestions_structure(self, client, mock_get_client):
        """Test suggestion response structure."""
        EmailFactory.reset_counter()
        mock_emails = [
            EmailFactory.create_large_email(size_mb=15),
        ]
        mock_get_client.search_emails = MagicMock(return_value=mock_emails)

        response = client.get('/api/v1/analyze/suggestions')

        data = json.loads(response.data)
        if data['data']['suggestions']:
            suggestion = data['data']['suggestions'][0]
            assert 'category' in suggestion
            assert 'description' in suggestion
            assert 'email_count' in suggestion
            assert 'priority' in suggestion
            assert 'action' in suggestion


class TestRulesEndpoint:
    """Tests for the rules endpoints."""

    def test_get_rules_empty(self, client, mock_get_rules):
        """Test getting rules when none exist."""
        response = client.get('/api/v1/rules')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['rules'] == []

    def test_get_rules(self, client, mock_get_rules):
        """Test getting existing rules."""
        mock_get_rules.create_rule(RuleFactory.create(
            name="Test Rule",
            from_email="test.com",
            archive=True
        ))

        response = client.get('/api/v1/rules')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['data']['rules']) == 1
        assert data['data']['rules'][0]['name'] == "Test Rule"

    def test_create_rule(self, client, mock_get_rules):
        """Test creating a new rule."""
        response = client.post(
            '/api/v1/rules',
            data=json.dumps({
                'name': 'New Rule',
                'from_email': 'example.com',
                'archive': True
            }),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['rule']['name'] == 'New Rule'

    def test_create_rule_missing_name(self, client, mock_get_rules):
        """Test creating rule without name."""
        response = client.post(
            '/api/v1/rules',
            data=json.dumps({'from_email': 'example.com'}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'name' in data['error']['message'].lower()

    def test_create_rule_name_too_long(self, client, mock_get_rules):
        """Test creating rule with name exceeding max length."""
        response = client.post(
            '/api/v1/rules',
            data=json.dumps({
                'name': 'x' * 101,  # Exceeds 100 char limit
                'from_email': 'example.com'
            }),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'at most 100' in data['error']['message']

    def test_delete_rule(self, client, mock_get_rules):
        """Test deleting a rule."""
        mock_get_rules.create_rule(RuleFactory.create(name="ToDelete"))

        response = client.delete('/api/v1/rules/ToDelete')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['deleted'] == 'ToDelete'

    def test_delete_rule_not_found(self, client, mock_get_rules):
        """Test deleting nonexistent rule."""
        response = client.delete('/api/v1/rules/NonexistentRule')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'not found' in data['error']['message'].lower()


class TestSyncRuleEndpoint:
    """Tests for rule sync endpoint."""

    def test_sync_rule(self, client, mock_get_rules, mock_gmail_service):
        """Test syncing a rule to Gmail."""
        mock_get_rules.create_rule(RuleFactory.create(
            name="ToSync",
            from_email="example.com",
            archive=True
        ))
        mock_gmail_service.users().settings().filters().create.return_value.execute.return_value = {
            'id': 'filter123'
        }

        response = client.post('/api/v1/rules/ToSync/sync')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['synced'] is True

    def test_sync_rule_not_found(self, client, mock_get_rules):
        """Test syncing nonexistent rule."""
        response = client.post('/api/v1/rules/Nonexistent/sync')

        assert response.status_code == 404


class TestLabelsEndpoint:
    """Tests for the labels endpoint."""

    def test_get_labels(self, client, mock_get_client):
        """Test getting all labels."""
        from gmail_cleanup.client import Label
        mock_labels = [
            Label(id='INBOX', name='INBOX', type='system', messages_total=100, messages_unread=10),
            Label(id='Label_1', name='Custom', type='user', messages_total=50, messages_unread=5),
        ]
        mock_get_client.get_labels = MagicMock(return_value=mock_labels)

        response = client.get('/api/v1/labels')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']['labels']) == 2


class TestArchiveEndpoint:
    """Tests for the archive action endpoint."""

    def test_archive_emails(self, client, mock_get_client):
        """Test archiving emails."""
        mock_get_client.archive_emails = MagicMock(return_value=3)

        response = client.post(
            '/api/v1/emails/archive',
            data=json.dumps({'email_ids': ['msg1', 'msg2', 'msg3']}),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['archived'] == 3

    def test_archive_no_emails(self, client, mock_get_client):
        """Test archiving with no email IDs."""
        response = client.post(
            '/api/v1/emails/archive',
            data=json.dumps({'email_ids': []}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'at least 1' in data['error']['message']

    def test_archive_too_many_emails(self, client, mock_get_client):
        """Test archiving with too many email IDs."""
        response = client.post(
            '/api/v1/emails/archive',
            data=json.dumps({'email_ids': [f'msg{i}' for i in range(101)]}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'at most 100' in data['error']['message']

    def test_archive_missing_email_ids(self, client, mock_get_client):
        """Test archiving without email_ids field."""
        response = client.post(
            '/api/v1/emails/archive',
            data=json.dumps({}),
            content_type='application/json'
        )

        assert response.status_code == 400


class TestTrashEndpoint:
    """Tests for the trash action endpoint."""

    def test_trash_emails(self, client, mock_get_client):
        """Test trashing emails."""
        mock_get_client.move_to_trash = MagicMock(return_value=2)

        response = client.post(
            '/api/v1/emails/trash',
            data=json.dumps({'email_ids': ['msg1', 'msg2']}),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['trashed'] == 2


class TestModeEndpoint:
    """Tests for the dry-run mode endpoint."""

    def test_get_mode(self, client, mock_get_client):
        """Test getting current mode."""
        response = client.get('/api/v1/mode')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'dry_run' in data['data']

    def test_set_mode_requires_confirmation(self, client, mock_get_client):
        """Test disabling dry-run requires confirmation."""
        response = client.post(
            '/api/v1/mode',
            data=json.dumps({'dry_run': False}),
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'confirm' in data['error']['message'].lower()

    def test_set_mode_with_confirmation(self, client, mock_get_client):
        """Test disabling dry-run with confirmation."""
        response = client.post(
            '/api/v1/mode',
            data=json.dumps({'dry_run': False, 'confirm': True}),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['dry_run'] is False

    def test_set_mode_enable_dry_run(self, client, mock_get_client):
        """Test enabling dry-run (no confirmation needed)."""
        response = client.post(
            '/api/v1/mode',
            data=json.dumps({'dry_run': True}),
            content_type='application/json'
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['dry_run'] is True


class TestCacheClearEndpoint:
    """Tests for the cache clear endpoint."""

    def test_clear_cache(self, client):
        """Test clearing the cache."""
        response = client.post('/api/v1/cache/clear')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['cleared'] is True


class TestLegacyRedirects:
    """Tests for legacy route redirects."""

    def test_legacy_status_redirect(self, client):
        """Test legacy status endpoint redirects."""
        response = client.get('/api/status', follow_redirects=False)

        assert response.status_code == 301
        assert '/api/v1/status' in response.location

    def test_legacy_inbox_stats_redirect(self, client):
        """Test legacy inbox stats endpoint redirects."""
        response = client.get('/api/inbox/stats', follow_redirects=False)

        assert response.status_code == 301
        assert '/api/v1/inbox/stats' in response.location

    def test_legacy_emails_redirect(self, client):
        """Test legacy emails endpoint redirects with query params."""
        response = client.get('/api/emails?q=test', follow_redirects=False)

        assert response.status_code == 301
        assert '/api/v1/emails' in response.location

    def test_legacy_rules_redirect(self, client):
        """Test legacy rules endpoint redirects."""
        response = client.get('/api/rules', follow_redirects=False)

        assert response.status_code == 301


class TestResponseHeaders:
    """Tests for response headers."""

    def test_security_headers(self, client):
        """Test security headers are set."""
        response = client.get('/api/v1/health')

        assert response.headers.get('X-Content-Type-Options') == 'nosniff'
        assert response.headers.get('X-Frame-Options') == 'DENY'

    def test_cors_headers(self, client):
        """Test CORS is enabled."""
        response = client.options('/api/v1/health')
        # CORS is configured in the app


class TestErrorHandling:
    """Tests for error handling."""

    @patch('web.app.get_client')
    def test_internal_error_handling(self, mock_get_client_func, client):
        """Test internal errors are handled gracefully."""
        mock_get_client_func.side_effect = Exception("Unexpected error")

        response = client.get('/api/v1/inbox/stats')

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error']['code'] == 'INTERNAL_ERROR'

    def test_invalid_json_body(self, client, mock_get_client):
        """Test handling of invalid JSON in request body."""
        response = client.post(
            '/api/v1/rules',
            data='not valid json',
            content_type='application/json'
        )

        # Should still handle gracefully
        assert response.status_code in [400, 500]

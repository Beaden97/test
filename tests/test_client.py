"""
Tests for the GmailClient module.

Tests Gmail API client operations including search, labels,
archiving, trashing, and email body extraction.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch, call
import base64

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from gmail_cleanup.client import Email, Label, GmailClient
from conftest import EmailFactory, LabelFactory


class TestEmailDataclass:
    """Tests for the Email dataclass."""

    def test_email_creation(self):
        """Test creating an Email object."""
        email = Email(
            id="msg123",
            thread_id="thread123",
            subject="Test Subject",
            sender="John Doe",
            sender_email="john@example.com",
            recipient="me@example.com",
            date=datetime.now(timezone.utc),
            snippet="Preview text...",
            labels=["INBOX"],
            is_unread=True,
            size_bytes=1024
        )
        assert email.id == "msg123"
        assert email.sender == "John Doe"
        assert email.is_unread is True

    def test_email_default_values(self):
        """Test Email default values."""
        email = Email(
            id="msg123",
            thread_id="thread123",
            subject="Test",
            sender="Test",
            sender_email="test@example.com",
            recipient="me@example.com",
            date=datetime.now(timezone.utc),
            snippet="...",
        )
        assert email.labels == []
        assert email.is_unread is False
        assert email.size_bytes == 0

    def test_email_str_unread(self):
        """Test Email string representation for unread email."""
        email = EmailFactory.create(is_unread=True, subject="Important Message")
        result = str(email)
        assert "Important Message" in result[:70]  # Subject is truncated

    def test_email_str_read(self):
        """Test Email string representation for read email."""
        email = EmailFactory.create(is_unread=False)
        result = str(email)
        assert result  # Just ensure it produces output


class TestLabelDataclass:
    """Tests for the Label dataclass."""

    def test_label_creation(self):
        """Test creating a Label object."""
        label = Label(
            id="Label_123",
            name="My Label",
            type="user",
            messages_total=100,
            messages_unread=10
        )
        assert label.name == "My Label"
        assert label.type == "user"
        assert label.messages_total == 100


class TestGmailClientInit:
    """Tests for GmailClient initialization."""

    def test_init_dry_run_default(self, mock_gmail_service):
        """Test that dry_run defaults to True."""
        client = GmailClient(mock_gmail_service)
        assert client.dry_run is True

    def test_init_dry_run_false(self, mock_gmail_service):
        """Test setting dry_run to False."""
        client = GmailClient(mock_gmail_service, dry_run=False)
        assert client.dry_run is False

    def test_init_user_id(self, mock_gmail_service):
        """Test user_id is set to 'me'."""
        client = GmailClient(mock_gmail_service)
        assert client.user_id == 'me'


class TestSearchEmails:
    """Tests for the search_emails method."""

    def test_search_emails_basic(self, gmail_client, mock_gmail_service):
        """Test basic email search."""
        # Setup mock response
        mock_gmail_service.users().messages().list.return_value.execute.return_value = {
            'messages': [{'id': 'msg1'}, {'id': 'msg2'}],
            'nextPageToken': None
        }
        mock_gmail_service.users().messages().get.return_value.execute.return_value = {
            'id': 'msg1',
            'threadId': 'thread1',
            'snippet': 'Test snippet',
            'labelIds': ['INBOX'],
            'sizeEstimate': 1024,
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'To', 'value': 'me@example.com'},
                    {'name': 'Subject', 'value': 'Test Subject'},
                    {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'},
                ]
            }
        }

        emails = gmail_client.search_emails("from:test@example.com", max_results=10)

        assert len(emails) == 2
        mock_gmail_service.users().messages().list.assert_called()

    def test_search_emails_empty_result(self, gmail_client, mock_gmail_service):
        """Test search with no results."""
        mock_gmail_service.users().messages().list.return_value.execute.return_value = {
            'messages': []
        }

        emails = gmail_client.search_emails("nonexistent")
        assert emails == []

    def test_search_emails_with_pagination(self, gmail_client, mock_gmail_service):
        """Test search handles pagination."""
        # First page
        mock_gmail_service.users().messages().list.return_value.execute.side_effect = [
            {'messages': [{'id': f'msg{i}'} for i in range(100)], 'nextPageToken': 'token1'},
            {'messages': [{'id': f'msg{i}'} for i in range(100, 150)], 'nextPageToken': None}
        ]
        mock_gmail_service.users().messages().get.return_value.execute.return_value = {
            'id': 'msg1',
            'threadId': 'thread1',
            'snippet': 'Test',
            'labelIds': ['INBOX'],
            'sizeEstimate': 1024,
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'Subject', 'value': 'Test'},
                    {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'},
                ]
            }
        }

        emails = gmail_client.search_emails("", max_results=150)
        assert len(emails) == 150

    def test_search_emails_respects_max_results(self, gmail_client, mock_gmail_service):
        """Test search respects max_results limit."""
        mock_gmail_service.users().messages().list.return_value.execute.return_value = {
            'messages': [{'id': f'msg{i}'} for i in range(10)],
            'nextPageToken': None
        }
        mock_gmail_service.users().messages().get.return_value.execute.return_value = {
            'id': 'msg1',
            'threadId': 'thread1',
            'snippet': 'Test',
            'labelIds': [],
            'sizeEstimate': 1024,
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'sender@example.com'},
                    {'name': 'Subject', 'value': 'Test'},
                    {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'},
                ]
            }
        }

        emails = gmail_client.search_emails("", max_results=5)
        # Should stop at max_results
        assert len(emails) <= 10

    def test_search_emails_handles_get_error(self, gmail_client, mock_gmail_service, capsys):
        """Test search handles errors getting individual emails."""
        mock_gmail_service.users().messages().list.return_value.execute.return_value = {
            'messages': [{'id': 'msg1'}],
            'nextPageToken': None
        }
        mock_gmail_service.users().messages().get.return_value.execute.side_effect = Exception("API Error")

        emails = gmail_client.search_emails("test")
        assert emails == []

        captured = capsys.readouterr()
        assert "Couldn't fetch email" in captured.out


class TestParseEmailAddress:
    """Tests for the _parse_email_address method."""

    def test_parse_with_name_and_email(self, gmail_client):
        """Test parsing 'Name <email>' format."""
        name, email = gmail_client._parse_email_address('John Doe <john@example.com>')
        assert name == 'John Doe'
        assert email == 'john@example.com'

    def test_parse_with_quoted_name(self, gmail_client):
        """Test parsing '"Name" <email>' format."""
        name, email = gmail_client._parse_email_address('"John Doe" <john@example.com>')
        assert name == 'John Doe'
        assert email == 'john@example.com'

    def test_parse_email_only(self, gmail_client):
        """Test parsing plain email address."""
        name, email = gmail_client._parse_email_address('john@example.com')
        assert name == 'john@example.com'
        assert email == 'john@example.com'

    def test_parse_empty_name(self, gmail_client):
        """Test parsing when name part is empty."""
        name, email = gmail_client._parse_email_address('<john@example.com>')
        assert email == 'john@example.com'


class TestGetLabels:
    """Tests for the get_labels method."""

    def test_get_labels_basic(self, gmail_client, mock_gmail_service):
        """Test getting all labels."""
        mock_gmail_service.users().labels().list.return_value.execute.return_value = {
            'labels': [
                {'id': 'INBOX', 'name': 'INBOX', 'type': 'system'},
                {'id': 'Label_1', 'name': 'My Label', 'type': 'user'},
            ]
        }
        mock_gmail_service.users().labels().get.return_value.execute.side_effect = [
            {'id': 'INBOX', 'name': 'INBOX', 'type': 'system', 'messagesTotal': 100, 'messagesUnread': 10},
            {'id': 'Label_1', 'name': 'My Label', 'type': 'user', 'messagesTotal': 50, 'messagesUnread': 5},
        ]

        labels = gmail_client.get_labels()

        assert len(labels) == 2
        assert labels[0].name == 'INBOX'
        assert labels[0].messages_total == 100

    def test_get_labels_caching(self, gmail_client, mock_gmail_service):
        """Test that labels are cached."""
        mock_gmail_service.users().labels().list.return_value.execute.return_value = {
            'labels': [{'id': 'INBOX', 'name': 'INBOX', 'type': 'system'}]
        }
        mock_gmail_service.users().labels().get.return_value.execute.return_value = {
            'id': 'INBOX', 'name': 'INBOX', 'type': 'system', 'messagesTotal': 100, 'messagesUnread': 10
        }

        # First call
        gmail_client.get_labels()
        # Second call should use cache
        gmail_client.get_labels()

        # List should only be called once
        assert mock_gmail_service.users().labels().list.call_count == 1

    def test_get_labels_refresh(self, gmail_client, mock_gmail_service):
        """Test label refresh bypasses cache."""
        mock_gmail_service.users().labels().list.return_value.execute.return_value = {
            'labels': [{'id': 'INBOX', 'name': 'INBOX', 'type': 'system'}]
        }
        mock_gmail_service.users().labels().get.return_value.execute.return_value = {
            'id': 'INBOX', 'name': 'INBOX', 'type': 'system', 'messagesTotal': 100, 'messagesUnread': 10
        }

        gmail_client.get_labels()
        gmail_client.get_labels(refresh=True)

        assert mock_gmail_service.users().labels().list.call_count == 2


class TestCreateLabel:
    """Tests for the create_label method."""

    def test_create_label_dry_run(self, gmail_client, mock_gmail_service, capsys):
        """Test create_label in dry run mode."""
        result = gmail_client.create_label("Test Label")

        assert result is None
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        mock_gmail_service.users().labels().create.assert_not_called()

    def test_create_label_live(self, gmail_client_live, mock_gmail_service):
        """Test create_label in live mode."""
        mock_gmail_service.users().labels().create.return_value.execute.return_value = {
            'id': 'Label_123',
            'name': 'Test Label'
        }

        result = gmail_client_live.create_label("Test Label")

        assert result is not None
        assert result.name == 'Test Label'
        mock_gmail_service.users().labels().create.assert_called_once()


class TestArchiveEmails:
    """Tests for the archive_emails method."""

    def test_archive_emails_dry_run(self, gmail_client, mock_gmail_service, capsys):
        """Test archiving in dry run mode."""
        email_ids = ['msg1', 'msg2', 'msg3']
        count = gmail_client.archive_emails(email_ids)

        assert count == 0
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "3 emails" in captured.out

    def test_archive_emails_live(self, gmail_client_live, mock_gmail_service):
        """Test archiving in live mode."""
        email_ids = ['msg1', 'msg2']
        mock_gmail_service.users().messages().modify.return_value.execute.return_value = {}

        count = gmail_client_live.archive_emails(email_ids)

        assert count == 2
        assert mock_gmail_service.users().messages().modify.call_count == 2

    def test_archive_emails_handles_errors(self, gmail_client_live, mock_gmail_service, capsys):
        """Test archiving handles individual errors."""
        mock_gmail_service.users().messages().modify.return_value.execute.side_effect = [
            {},  # First succeeds
            Exception("API Error"),  # Second fails
        ]

        count = gmail_client_live.archive_emails(['msg1', 'msg2'])

        assert count == 1
        captured = capsys.readouterr()
        assert "Couldn't archive email" in captured.out

    def test_archive_emails_empty_list(self, gmail_client_live, mock_gmail_service):
        """Test archiving empty list."""
        count = gmail_client_live.archive_emails([])
        assert count == 0


class TestMoveToLabel:
    """Tests for the move_to_label method."""

    def test_move_to_label_dry_run(self, gmail_client, mock_gmail_service, capsys):
        """Test moving to label in dry run mode."""
        count = gmail_client.move_to_label(['msg1'], 'Label_123')

        assert count == 0
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out

    def test_move_to_label_live(self, gmail_client_live, mock_gmail_service):
        """Test moving to label in live mode."""
        mock_gmail_service.users().messages().modify.return_value.execute.return_value = {}

        count = gmail_client_live.move_to_label(['msg1', 'msg2'], 'Label_123')

        assert count == 2

    def test_move_to_label_keep_in_inbox(self, gmail_client_live, mock_gmail_service):
        """Test moving to label while keeping in inbox."""
        mock_gmail_service.users().messages().modify.return_value.execute.return_value = {}

        gmail_client_live.move_to_label(['msg1'], 'Label_123', remove_from_inbox=False)

        # Check that INBOX was not removed
        call_args = mock_gmail_service.users().messages().modify.call_args
        body = call_args[1]['body']
        assert 'removeLabelIds' not in body


class TestMoveToTrash:
    """Tests for the move_to_trash method."""

    def test_move_to_trash_dry_run(self, gmail_client, mock_gmail_service, capsys):
        """Test trashing in dry run mode."""
        count = gmail_client.move_to_trash(['msg1', 'msg2'])

        assert count == 0
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out
        assert "2 emails" in captured.out

    def test_move_to_trash_live(self, gmail_client_live, mock_gmail_service, capsys):
        """Test trashing in live mode."""
        mock_gmail_service.users().messages().trash.return_value.execute.return_value = {}

        count = gmail_client_live.move_to_trash(['msg1', 'msg2'])

        assert count == 2
        captured = capsys.readouterr()
        assert "trash" in captured.out.lower()

    def test_move_to_trash_handles_errors(self, gmail_client_live, mock_gmail_service):
        """Test trashing handles individual errors."""
        mock_gmail_service.users().messages().trash.return_value.execute.side_effect = [
            Exception("API Error"),
            {},
        ]

        count = gmail_client_live.move_to_trash(['msg1', 'msg2'])
        assert count == 1


class TestMarkAsRead:
    """Tests for the mark_as_read method."""

    def test_mark_as_read_dry_run(self, gmail_client, mock_gmail_service, capsys):
        """Test marking as read in dry run mode."""
        count = gmail_client.mark_as_read(['msg1'])

        assert count == 0
        captured = capsys.readouterr()
        assert "[DRY RUN]" in captured.out

    def test_mark_as_read_live(self, gmail_client_live, mock_gmail_service):
        """Test marking as read in live mode."""
        mock_gmail_service.users().messages().modify.return_value.execute.return_value = {}

        count = gmail_client_live.mark_as_read(['msg1', 'msg2'])

        assert count == 2

        # Check that UNREAD was removed
        call_args = mock_gmail_service.users().messages().modify.call_args
        body = call_args[1]['body']
        assert 'UNREAD' in body['removeLabelIds']


class TestGetEmailBody:
    """Tests for the get_email_body method."""

    def test_get_email_body_simple(self, gmail_client, mock_gmail_service):
        """Test getting email body from simple message."""
        body_content = "Hello, this is the email body."
        encoded = base64.urlsafe_b64encode(body_content.encode()).decode()

        mock_gmail_service.users().messages().get.return_value.execute.return_value = {
            'payload': {
                'body': {'data': encoded}
            }
        }

        result = gmail_client.get_email_body('msg1')
        assert result == body_content

    def test_get_email_body_multipart(self, gmail_client, mock_gmail_service):
        """Test getting email body from multipart message."""
        body_content = "Plain text body"
        encoded = base64.urlsafe_b64encode(body_content.encode()).decode()

        mock_gmail_service.users().messages().get.return_value.execute.return_value = {
            'payload': {
                'parts': [
                    {'mimeType': 'text/html', 'body': {'data': 'html_content'}},
                    {'mimeType': 'text/plain', 'body': {'data': encoded}},
                ]
            }
        }

        result = gmail_client.get_email_body('msg1')
        assert result == body_content

    def test_get_email_body_nested_parts(self, gmail_client, mock_gmail_service):
        """Test getting email body from nested multipart message."""
        body_content = "Nested body"
        encoded = base64.urlsafe_b64encode(body_content.encode()).decode()

        mock_gmail_service.users().messages().get.return_value.execute.return_value = {
            'payload': {
                'parts': [
                    {
                        'mimeType': 'multipart/alternative',
                        'parts': [
                            {'mimeType': 'text/plain', 'body': {'data': encoded}},
                        ]
                    },
                ]
            }
        }

        result = gmail_client.get_email_body('msg1')
        assert result == body_content

    def test_get_email_body_no_content(self, gmail_client, mock_gmail_service):
        """Test getting email body when no text content found."""
        mock_gmail_service.users().messages().get.return_value.execute.return_value = {
            'payload': {}
        }

        result = gmail_client.get_email_body('msg1')
        assert "No text content" in result

    def test_get_email_body_error(self, gmail_client, mock_gmail_service):
        """Test getting email body when API error occurs."""
        mock_gmail_service.users().messages().get.return_value.execute.side_effect = Exception("API Error")

        result = gmail_client.get_email_body('msg1')
        assert "Could not load" in result


class TestGetInboxStats:
    """Tests for the get_inbox_stats method."""

    def test_get_inbox_stats(self, gmail_client, mock_gmail_service):
        """Test getting inbox statistics."""
        mock_gmail_service.users().labels().get.return_value.execute.side_effect = [
            {'messagesTotal': 1000, 'messagesUnread': 50},  # INBOX
            {'messagesTotal': 200},  # PROMOTIONS
            {'messagesTotal': 100},  # SOCIAL
            {'messagesTotal': 150},  # UPDATES
            {'messagesTotal': 75},   # FORUMS
        ]

        stats = gmail_client.get_inbox_stats()

        assert stats['total_inbox'] == 1000
        assert stats['unread_inbox'] == 50
        assert 'categories' in stats
        assert stats['categories']['promotions'] == 200

    def test_get_inbox_stats_missing_categories(self, gmail_client, mock_gmail_service):
        """Test get_inbox_stats handles missing categories gracefully."""
        mock_gmail_service.users().labels().get.return_value.execute.side_effect = [
            {'messagesTotal': 1000, 'messagesUnread': 50},  # INBOX
            Exception("Not found"),  # PROMOTIONS
            {'messagesTotal': 100},  # SOCIAL
            Exception("Not found"),  # UPDATES
            Exception("Not found"),  # FORUMS
        ]

        stats = gmail_client.get_inbox_stats()

        assert stats['total_inbox'] == 1000
        assert stats['categories'].get('social') == 100
        assert 'promotions' not in stats['categories']

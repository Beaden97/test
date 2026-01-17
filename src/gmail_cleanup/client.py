"""
Gmail Client Module

This is the main interface for reading and organizing your emails.
Think of it as a helper that talks to Gmail for you.
"""

import base64
import email
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from googleapiclient.discovery import Resource


@dataclass
class Email:
    """
    Represents a single email.

    This is a simple container that holds all the important
    information about an email in an easy-to-use format.
    """
    id: str
    thread_id: str
    subject: str
    sender: str
    sender_email: str
    recipient: str
    date: datetime
    snippet: str  # Preview of the email content
    labels: list[str] = field(default_factory=list)
    is_unread: bool = False
    size_bytes: int = 0

    def __str__(self):
        status = "📬" if self.is_unread else "📭"
        return f"{status} {self.date.strftime('%Y-%m-%d')} | {self.sender[:20]:<20} | {self.subject[:50]}"


@dataclass
class Label:
    """
    Represents a Gmail label (folder).
    """
    id: str
    name: str
    type: str  # 'system' or 'user'
    messages_total: int = 0
    messages_unread: int = 0


class GmailClient:
    """
    Main Gmail client for reading and organizing emails.

    SAFETY FIRST: This client has a "dry run" mode that shows
    what WOULD happen without actually doing anything.
    """

    def __init__(self, service: Resource, dry_run: bool = True):
        """
        Create a new Gmail client.

        Args:
            service: Gmail API service (from GmailAuth.get_service())
            dry_run: If True, don't actually modify anything (safe mode)
        """
        self.service = service
        self.dry_run = dry_run
        self.user_id = 'me'  # Special value meaning "the logged-in user"

        # Cache for labels
        self._labels_cache: dict[str, Label] = {}

    def search_emails(
        self,
        query: str = "",
        max_results: int = 100,
        include_spam_trash: bool = False
    ) -> list[Email]:
        """
        Search for emails matching a query.

        Args:
            query: Gmail search query (same as the Gmail search box)
                   Examples:
                   - "from:amazon.com" - emails from Amazon
                   - "is:unread" - unread emails
                   - "older_than:1y" - emails older than 1 year
                   - "has:attachment larger:5M" - large attachments
            max_results: Maximum number of emails to return
            include_spam_trash: Include spam and trash folders

        Returns:
            List of Email objects matching the search
        """
        emails = []
        page_token = None

        while len(emails) < max_results:
            # Fetch a page of message IDs
            results = self.service.users().messages().list(
                userId=self.user_id,
                q=query,
                maxResults=min(100, max_results - len(emails)),
                pageToken=page_token,
                includeSpamTrash=include_spam_trash
            ).execute()

            messages = results.get('messages', [])
            if not messages:
                break

            # Fetch full details for each message
            for msg in messages:
                email_obj = self._get_email_details(msg['id'])
                if email_obj:
                    emails.append(email_obj)

            page_token = results.get('nextPageToken')
            if not page_token:
                break

        return emails

    def _get_email_details(self, message_id: str) -> Optional[Email]:
        """
        Get full details of a single email.
        """
        try:
            msg = self.service.users().messages().get(
                userId=self.user_id,
                id=message_id,
                format='metadata',
                metadataHeaders=['From', 'To', 'Subject', 'Date']
            ).execute()

            headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}

            # Parse the From header to get name and email
            from_header = headers.get('From', 'Unknown')
            sender_name, sender_email = self._parse_email_address(from_header)

            # Parse date
            date_str = headers.get('Date', '')
            try:
                date = email.utils.parsedate_to_datetime(date_str)
            except Exception:
                date = datetime.now()

            return Email(
                id=msg['id'],
                thread_id=msg['threadId'],
                subject=headers.get('Subject', '(No Subject)'),
                sender=sender_name,
                sender_email=sender_email,
                recipient=headers.get('To', ''),
                date=date,
                snippet=msg.get('snippet', ''),
                labels=msg.get('labelIds', []),
                is_unread='UNREAD' in msg.get('labelIds', []),
                size_bytes=int(msg.get('sizeEstimate', 0))
            )
        except Exception as e:
            print(f"⚠️  Couldn't fetch email {message_id}: {e}")
            return None

    def _parse_email_address(self, from_header: str) -> tuple[str, str]:
        """
        Parse "John Doe <john@example.com>" into ("John Doe", "john@example.com")
        """
        if '<' in from_header and '>' in from_header:
            name = from_header.split('<')[0].strip().strip('"')
            email_addr = from_header.split('<')[1].split('>')[0]
            return (name or email_addr, email_addr)
        return (from_header, from_header)

    def get_labels(self, refresh: bool = False) -> list[Label]:
        """
        Get all labels (folders) in your Gmail.

        Args:
            refresh: Force refresh the cache

        Returns:
            List of Label objects
        """
        if self._labels_cache and not refresh:
            return list(self._labels_cache.values())

        results = self.service.users().labels().list(userId=self.user_id).execute()
        labels = []

        for label_data in results.get('labels', []):
            # Get detailed info for each label
            label_info = self.service.users().labels().get(
                userId=self.user_id,
                id=label_data['id']
            ).execute()

            label = Label(
                id=label_info['id'],
                name=label_info['name'],
                type=label_info['type'],
                messages_total=label_info.get('messagesTotal', 0),
                messages_unread=label_info.get('messagesUnread', 0)
            )
            labels.append(label)
            self._labels_cache[label.id] = label

        return labels

    def create_label(self, name: str) -> Optional[Label]:
        """
        Create a new label (folder).

        Args:
            name: Name for the new label

        Returns:
            The created Label, or None if in dry_run mode
        """
        if self.dry_run:
            print(f"🔹 [DRY RUN] Would create label: {name}")
            return None

        label_body = {
            'name': name,
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show'
        }

        result = self.service.users().labels().create(
            userId=self.user_id,
            body=label_body
        ).execute()

        label = Label(
            id=result['id'],
            name=result['name'],
            type='user'
        )
        self._labels_cache[label.id] = label
        print(f"✅ Created label: {name}")
        return label

    def archive_emails(self, email_ids: list[str]) -> int:
        """
        Archive emails (remove from inbox but keep them).

        This is SAFE - emails are not deleted, just moved out of inbox.

        Args:
            email_ids: List of email IDs to archive

        Returns:
            Number of emails archived
        """
        if self.dry_run:
            print(f"🔹 [DRY RUN] Would archive {len(email_ids)} emails")
            return 0

        count = 0
        for email_id in email_ids:
            try:
                self.service.users().messages().modify(
                    userId=self.user_id,
                    id=email_id,
                    body={'removeLabelIds': ['INBOX']}
                ).execute()
                count += 1
            except Exception as e:
                print(f"⚠️  Couldn't archive email {email_id}: {e}")

        print(f"✅ Archived {count} emails")
        return count

    def move_to_label(self, email_ids: list[str], label_id: str, remove_from_inbox: bool = True) -> int:
        """
        Move emails to a specific label/folder.

        Args:
            email_ids: List of email IDs to move
            label_id: Target label ID
            remove_from_inbox: Also remove from inbox (default: True)

        Returns:
            Number of emails moved
        """
        if self.dry_run:
            label_name = self._labels_cache.get(label_id, Label(label_id, label_id, 'user')).name
            print(f"🔹 [DRY RUN] Would move {len(email_ids)} emails to '{label_name}'")
            return 0

        count = 0
        for email_id in email_ids:
            try:
                body = {'addLabelIds': [label_id]}
                if remove_from_inbox:
                    body['removeLabelIds'] = ['INBOX']

                self.service.users().messages().modify(
                    userId=self.user_id,
                    id=email_id,
                    body=body
                ).execute()
                count += 1
            except Exception as e:
                print(f"⚠️  Couldn't move email {email_id}: {e}")

        print(f"✅ Moved {count} emails")
        return count

    def move_to_trash(self, email_ids: list[str]) -> int:
        """
        Move emails to trash.

        SAFE: Emails go to trash first (can be recovered for 30 days).
        They are NOT permanently deleted.

        Args:
            email_ids: List of email IDs to trash

        Returns:
            Number of emails trashed
        """
        if self.dry_run:
            print(f"🔹 [DRY RUN] Would move {len(email_ids)} emails to trash")
            return 0

        count = 0
        for email_id in email_ids:
            try:
                self.service.users().messages().trash(
                    userId=self.user_id,
                    id=email_id
                ).execute()
                count += 1
            except Exception as e:
                print(f"⚠️  Couldn't trash email {email_id}: {e}")

        print(f"🗑️  Moved {count} emails to trash (recoverable for 30 days)")
        return count

    def mark_as_read(self, email_ids: list[str]) -> int:
        """
        Mark emails as read.

        Args:
            email_ids: List of email IDs to mark as read

        Returns:
            Number of emails marked as read
        """
        if self.dry_run:
            print(f"🔹 [DRY RUN] Would mark {len(email_ids)} emails as read")
            return 0

        count = 0
        for email_id in email_ids:
            try:
                self.service.users().messages().modify(
                    userId=self.user_id,
                    id=email_id,
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
                count += 1
            except Exception as e:
                print(f"⚠️  Couldn't mark email {email_id} as read: {e}")

        print(f"✅ Marked {count} emails as read")
        return count

    def get_email_body(self, email_id: str) -> str:
        """
        Get the full body/content of an email.

        Args:
            email_id: The email ID

        Returns:
            The email body as plain text
        """
        try:
            msg = self.service.users().messages().get(
                userId=self.user_id,
                id=email_id,
                format='full'
            ).execute()

            return self._extract_body(msg.get('payload', {}))
        except Exception as e:
            return f"[Could not load email body: {e}]"

    def _extract_body(self, payload: dict) -> str:
        """
        Extract readable text from email payload.
        """
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')

        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    if part.get('body', {}).get('data'):
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')

                # Recurse into nested parts
                if 'parts' in part:
                    result = self._extract_body(part)
                    if result:
                        return result

        return "[No text content found]"

    def get_inbox_stats(self) -> dict:
        """
        Get statistics about your inbox.

        Returns:
            Dictionary with inbox statistics
        """
        # Get inbox label info
        inbox = self.service.users().labels().get(
            userId=self.user_id,
            id='INBOX'
        ).execute()

        # Get some category counts
        categories = {}
        for category in ['CATEGORY_PROMOTIONS', 'CATEGORY_SOCIAL', 'CATEGORY_UPDATES', 'CATEGORY_FORUMS']:
            try:
                cat_info = self.service.users().labels().get(
                    userId=self.user_id,
                    id=category
                ).execute()
                categories[category.replace('CATEGORY_', '').lower()] = cat_info.get('messagesTotal', 0)
            except Exception:
                pass

        return {
            'total_inbox': inbox.get('messagesTotal', 0),
            'unread_inbox': inbox.get('messagesUnread', 0),
            'categories': categories
        }

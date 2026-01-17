"""
Gmail Rules/Filters Module

This helps you create Gmail filters that automatically
organize your incoming emails. Think of filters like
sorting rules: "Emails from Amazon → go to Shopping folder"
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from googleapiclient.discovery import Resource


@dataclass
class Rule:
    """
    A rule for organizing emails.

    Think of it like a sorting instruction:
    "When [condition], do [action]"

    Example:
    - When email is from "amazon.com"
    - Archive it and add "Shopping" label
    """
    name: str  # Human-friendly name
    from_email: Optional[str] = None  # Match sender email/domain
    to_email: Optional[str] = None  # Match recipient
    subject_contains: Optional[str] = None  # Match subject text
    has_words: Optional[str] = None  # Match any words in email

    # Actions to take
    add_label: Optional[str] = None  # Add this label
    remove_label: Optional[str] = None  # Remove this label
    archive: bool = False  # Remove from inbox (but keep email)
    mark_read: bool = False  # Mark as read
    star: bool = False  # Add a star
    never_spam: bool = False  # Never mark as spam
    forward_to: Optional[str] = None  # Forward to another email

    # Internal
    gmail_filter_id: Optional[str] = None  # ID if synced to Gmail

    def __str__(self):
        conditions = []
        if self.from_email:
            conditions.append(f"from:{self.from_email}")
        if self.to_email:
            conditions.append(f"to:{self.to_email}")
        if self.subject_contains:
            conditions.append(f"subject:{self.subject_contains}")
        if self.has_words:
            conditions.append(f"has:{self.has_words}")

        actions = []
        if self.add_label:
            actions.append(f"→ {self.add_label}")
        if self.archive:
            actions.append("→ Archive")
        if self.mark_read:
            actions.append("→ Mark read")

        return f"{self.name}: {' AND '.join(conditions)} {' '.join(actions)}"


class RuleManager:
    """
    Manages email organization rules.

    Rules are saved locally AND can be synced to Gmail as filters.
    Local rules = only this tool sees them
    Gmail filters = Gmail applies them automatically to new emails
    """

    def __init__(self, service: Resource, rules_file: str = "data/rules.json"):
        """
        Create a rule manager.

        Args:
            service: Gmail API service (from GmailAuth)
            rules_file: Where to save rules locally
        """
        self.service = service
        self.rules_file = Path(rules_file)
        self.rules: list[Rule] = []
        self._label_cache: dict[str, str] = {}  # name -> id

        # Load existing rules
        self._load_rules()

    def _load_rules(self):
        """
        Load rules from local file.
        """
        if self.rules_file.exists():
            try:
                with open(self.rules_file, 'r') as f:
                    data = json.load(f)
                    self.rules = [Rule(**r) for r in data.get('rules', [])]
                print(f"📋 Loaded {len(self.rules)} saved rules")
            except Exception as e:
                print(f"⚠️  Couldn't load rules: {e}")
                self.rules = []

    def _save_rules(self):
        """
        Save rules to local file.
        """
        self.rules_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'rules': [
                {k: v for k, v in r.__dict__.items() if v is not None and v != False}
                for r in self.rules
            ]
        }

        with open(self.rules_file, 'w') as f:
            json.dump(data, f, indent=2)

    def create_rule(self, rule: Rule) -> Rule:
        """
        Create a new rule (saved locally).

        Args:
            rule: The rule to create

        Returns:
            The created rule
        """
        self.rules.append(rule)
        self._save_rules()
        print(f"✅ Created rule: {rule.name}")
        return rule

    def delete_rule(self, rule_name: str) -> bool:
        """
        Delete a rule by name.

        Args:
            rule_name: Name of the rule to delete

        Returns:
            True if deleted, False if not found
        """
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                # If synced to Gmail, remove from there too
                if rule.gmail_filter_id:
                    try:
                        self.service.users().settings().filters().delete(
                            userId='me',
                            id=rule.gmail_filter_id
                        ).execute()
                        print(f"🗑️  Removed Gmail filter for: {rule_name}")
                    except Exception as e:
                        print(f"⚠️  Couldn't remove Gmail filter: {e}")

                self.rules.pop(i)
                self._save_rules()
                print(f"✅ Deleted rule: {rule_name}")
                return True

        print(f"❌ Rule not found: {rule_name}")
        return False

    def list_rules(self) -> list[Rule]:
        """
        Get all saved rules.
        """
        return self.rules

    def sync_to_gmail(self, rule: Rule) -> bool:
        """
        Sync a rule to Gmail as a filter.

        After syncing, Gmail will automatically apply this rule
        to ALL new incoming emails!

        Args:
            rule: The rule to sync

        Returns:
            True if synced successfully
        """
        # Build the filter criteria
        criteria = {}
        if rule.from_email:
            criteria['from'] = rule.from_email
        if rule.to_email:
            criteria['to'] = rule.to_email
        if rule.subject_contains:
            criteria['subject'] = rule.subject_contains
        if rule.has_words:
            criteria['query'] = rule.has_words

        if not criteria:
            print("❌ Rule needs at least one condition (from, to, subject, or has_words)")
            return False

        # Build the actions
        action = {}
        if rule.add_label:
            label_id = self._get_or_create_label(rule.add_label)
            if label_id:
                action['addLabelIds'] = [label_id]

        if rule.remove_label:
            label_id = self._get_label_id(rule.remove_label)
            if label_id:
                action['removeLabelIds'] = [label_id]

        if rule.archive:
            action.setdefault('removeLabelIds', []).append('INBOX')

        if rule.mark_read:
            action.setdefault('removeLabelIds', []).append('UNREAD')

        if rule.star:
            action.setdefault('addLabelIds', []).append('STARRED')

        if rule.forward_to:
            action['forward'] = rule.forward_to

        if not action:
            print("❌ Rule needs at least one action")
            return False

        # Create the Gmail filter
        filter_body = {
            'criteria': criteria,
            'action': action
        }

        try:
            result = self.service.users().settings().filters().create(
                userId='me',
                body=filter_body
            ).execute()

            rule.gmail_filter_id = result['id']
            self._save_rules()
            print(f"✅ Synced to Gmail! Filter ID: {result['id']}")
            print("   Gmail will now apply this rule to all new emails")
            return True

        except Exception as e:
            print(f"❌ Couldn't create Gmail filter: {e}")
            return False

    def get_gmail_filters(self) -> list[dict]:
        """
        Get all existing Gmail filters.

        Returns:
            List of Gmail filter data
        """
        try:
            result = self.service.users().settings().filters().list(
                userId='me'
            ).execute()
            return result.get('filter', [])
        except Exception as e:
            print(f"⚠️  Couldn't fetch Gmail filters: {e}")
            return []

    def _get_label_id(self, label_name: str) -> Optional[str]:
        """
        Get the ID of a label by name.
        """
        if label_name in self._label_cache:
            return self._label_cache[label_name]

        try:
            result = self.service.users().labels().list(userId='me').execute()
            for label in result.get('labels', []):
                if label['name'].lower() == label_name.lower():
                    self._label_cache[label_name] = label['id']
                    return label['id']
        except Exception:
            pass

        return None

    def _get_or_create_label(self, label_name: str) -> Optional[str]:
        """
        Get a label ID, creating it if it doesn't exist.
        """
        # Check if it exists
        label_id = self._get_label_id(label_name)
        if label_id:
            return label_id

        # Create it
        try:
            label_body = {
                'name': label_name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
            result = self.service.users().labels().create(
                userId='me',
                body=label_body
            ).execute()
            self._label_cache[label_name] = result['id']
            print(f"📁 Created new label: {label_name}")
            return result['id']
        except Exception as e:
            print(f"⚠️  Couldn't create label {label_name}: {e}")
            return None

    def apply_rule_to_existing(
        self,
        rule: Rule,
        max_emails: int = 100,
        dry_run: bool = True
    ) -> int:
        """
        Apply a rule to existing emails in your inbox.

        This is different from syncing to Gmail:
        - sync_to_gmail = affects NEW emails automatically
        - apply_to_existing = affects emails already in your inbox

        Args:
            rule: The rule to apply
            max_emails: Maximum emails to process
            dry_run: If True, show what would happen without doing it

        Returns:
            Number of emails affected
        """
        # Build search query
        query_parts = []
        if rule.from_email:
            query_parts.append(f"from:{rule.from_email}")
        if rule.to_email:
            query_parts.append(f"to:{rule.to_email}")
        if rule.subject_contains:
            query_parts.append(f"subject:{rule.subject_contains}")
        if rule.has_words:
            query_parts.append(rule.has_words)

        if not query_parts:
            print("❌ Rule needs at least one condition")
            return 0

        query = ' '.join(query_parts)

        # Find matching emails
        try:
            result = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_emails
            ).execute()

            messages = result.get('messages', [])
            if not messages:
                print(f"📭 No emails match: {query}")
                return 0

            print(f"📬 Found {len(messages)} matching emails")

            if dry_run:
                print("🔹 [DRY RUN] Would apply rule to these emails")
                return len(messages)

            # Apply the rule
            count = 0
            for msg in messages:
                try:
                    body = {}

                    if rule.add_label:
                        label_id = self._get_or_create_label(rule.add_label)
                        if label_id:
                            body.setdefault('addLabelIds', []).append(label_id)

                    if rule.archive:
                        body.setdefault('removeLabelIds', []).append('INBOX')

                    if rule.mark_read:
                        body.setdefault('removeLabelIds', []).append('UNREAD')

                    if rule.star:
                        body.setdefault('addLabelIds', []).append('STARRED')

                    if body:
                        self.service.users().messages().modify(
                            userId='me',
                            id=msg['id'],
                            body=body
                        ).execute()
                        count += 1

                except Exception as e:
                    print(f"⚠️  Couldn't process email {msg['id']}: {e}")

            print(f"✅ Applied rule to {count} emails")
            return count

        except Exception as e:
            print(f"❌ Error searching emails: {e}")
            return 0


# Helper function to create common rules quickly
def quick_rule(
    name: str,
    from_domain: str,
    action: str = "archive",
    label: Optional[str] = None
) -> Rule:
    """
    Create a common rule quickly.

    Examples:
        # Archive all emails from linkedin.com
        quick_rule("LinkedIn", "linkedin.com", "archive")

        # Label Amazon emails as Shopping
        quick_rule("Amazon", "amazon.com", "label", "Shopping")

        # Archive and label newsletter emails
        quick_rule("Newsletters", "newsletter", "both", "Newsletters")
    """
    rule = Rule(name=name, from_email=from_domain)

    if action == "archive" or action == "both":
        rule.archive = True

    if action == "label" or action == "both":
        rule.add_label = label or name

    if action == "read":
        rule.mark_read = True

    return rule

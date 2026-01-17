"""
Gmail OAuth2 Authentication Module

This handles connecting to your Gmail account securely.
It can use your EXISTING login from the email skill, so
you don't need to log in again!

Your existing credentials are in: ~/.claude/.google/
"""

import json
import os
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource


# These are the permissions we need from Gmail
# Your existing email skill already has these!
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.labels',
    'https://www.googleapis.com/auth/gmail.settings.basic',
]

# Default paths - matches your existing email skill setup
DEFAULT_CREDENTIALS_PATH = Path.home() / ".claude" / ".google" / "client_secret.json"
DEFAULT_TOKEN_PATH = Path.home() / ".claude" / ".google" / "token.json"


class GmailAuth:
    """
    Handles Gmail authentication.

    GOOD NEWS: If you've used the email skill before,
    this will use your existing login automatically!
    """

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None
    ):
        """
        Set up authentication.

        Args:
            credentials_path: Where your Google credentials are
                            (default: ~/.claude/.google/client_secret.json)
            token_path: Where your login token is stored
                       (default: ~/.claude/.google/token.json)
        """
        self.credentials_path = Path(credentials_path) if credentials_path else DEFAULT_CREDENTIALS_PATH
        self.token_path = Path(token_path) if token_path else DEFAULT_TOKEN_PATH
        self.creds: Optional[Credentials] = None

    def authenticate(self) -> Credentials:
        """
        Log in to Gmail (or use existing login).

        Returns:
            Your Gmail credentials (proof that you're logged in)
        """
        # Try to load existing token from JSON (from email skill)
        if self.token_path.exists():
            print(f"✅ Found existing login at {self.token_path}")
            self.creds = self._load_token_json()

        # If no login or it's expired, we need to refresh or re-login
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                # Token expired but we can refresh it (no browser needed)
                print("🔄 Refreshing your Gmail login...")
                try:
                    self.creds.refresh(Request())
                    self._save_token_json()
                    print("✅ Login refreshed!")
                except Exception as e:
                    print(f"⚠️  Couldn't refresh token: {e}")
                    self.creds = None

            if not self.creds:
                # Need to log in through browser
                self._do_fresh_login()

        return self.creds

    def _load_token_json(self) -> Optional[Credentials]:
        """
        Load credentials from JSON token file (compatible with email skill).
        """
        try:
            with open(self.token_path, 'r') as f:
                token_data = json.load(f)

            return Credentials(
                token=token_data.get('access_token') or token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes', SCOPES)
            )
        except Exception as e:
            print(f"⚠️  Couldn't load existing token: {e}")
            return None

    def _save_token_json(self):
        """
        Save credentials to JSON token file.
        """
        if not self.creds:
            return

        token_data = {
            'access_token': self.creds.token,
            'refresh_token': self.creds.refresh_token,
            'token_uri': self.creds.token_uri,
            'client_id': self.creds.client_id,
            'client_secret': self.creds.client_secret,
            'scopes': list(self.creds.scopes) if self.creds.scopes else SCOPES
        }

        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_path, 'w') as f:
            json.dump(token_data, f, indent=2)

    def _do_fresh_login(self):
        """
        Perform fresh OAuth login through browser.
        """
        if not self.credentials_path.exists():
            raise FileNotFoundError(
                f"❌ Can't find credentials at {self.credentials_path}\n\n"
                "You need Google Cloud credentials to use this tool.\n"
                "If you've used the email skill before, check that your\n"
                "credentials are at: ~/.claude/.google/client_secret.json\n\n"
                "See README.md for setup instructions."
            )

        print("🔐 Opening browser for Gmail login...")
        print("   (You'll only need to do this once)")

        flow = InstalledAppFlow.from_client_secrets_file(
            str(self.credentials_path), SCOPES
        )
        self.creds = flow.run_local_server(port=0)
        self._save_token_json()
        print("✅ Login saved!")

    def get_service(self) -> Resource:
        """
        Get a Gmail API connection.

        Returns:
            A Gmail API service - your connection to Gmail
        """
        if not self.creds:
            self.authenticate()

        return build('gmail', 'v1', credentials=self.creds)

    def logout(self):
        """
        Remove saved login (you'll need to log in again next time).

        Note: This only affects this tool. Your email skill
        will still work.
        """
        if self.token_path.exists():
            print(f"⚠️  This would delete {self.token_path}")
            print("   This might affect your email skill too!")
            print("   (Not deleting - just clearing local cache)")
        self.creds = None

    def is_authenticated(self) -> bool:
        """
        Check if we're currently logged in.
        """
        if not self.token_path.exists():
            return False

        try:
            creds = self._load_token_json()
            return creds is not None and creds.valid
        except Exception:
            return False

    def get_status(self) -> dict:
        """
        Get detailed authentication status.

        Returns:
            Dictionary with auth status info
        """
        return {
            'credentials_exist': self.credentials_path.exists(),
            'credentials_path': str(self.credentials_path),
            'token_exists': self.token_path.exists(),
            'token_path': str(self.token_path),
            'is_authenticated': self.is_authenticated(),
        }

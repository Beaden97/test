#!/usr/bin/env python3
"""
Gmail Inbox Cleanup Assistant

A friendly tool to help you organize your inbox.
Run this file to start the interactive cleanup session.

Usage:
    python cleanup.py          # Safe mode (preview changes)
    python cleanup.py --live   # Live mode (actually make changes)
"""

from src.cli.interactive import main

if __name__ == "__main__":
    main()

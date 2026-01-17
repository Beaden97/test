#!/usr/bin/env python3
"""
Gmail Cleanup Web UI

A visual way to browse and organize your emails.
Open http://localhost:5000 in your browser after running.

Usage:
    python web.py
"""

from src.web.app import run_server

if __name__ == "__main__":
    run_server(debug=True)

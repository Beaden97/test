# 📧 Gmail Inbox Cleanup Assistant

An ADHD-friendly tool to help you organize your Gmail inbox. Work together with Claude to clean up emails and create rules for auto-organization.

## ✨ Features

- **🔍 Quick Scan** - Find easy cleanup opportunities (newsletters, old emails, large attachments)
- **👥 Sender Analysis** - See who emails you most and batch-organize by sender
- **📝 Rule Creation** - Create Gmail filters that auto-organize future emails
- **🔒 Safe Mode** - Preview all changes before they happen (nothing deleted without approval)
- **🌐 Two Interfaces** - CLI for quick actions, Web UI for visual browsing

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Connect to Gmail

**If you already have the email skill set up:** You're good to go! This tool uses the same credentials from `~/.claude/.google/`.

**If you're starting fresh:** See [Setting Up Gmail Credentials](#setting-up-gmail-credentials) below.

### 3. Run the Tool

**Interactive CLI (recommended):**
```bash
python cleanup.py
```

**Web UI:**
```bash
python web.py
# Then open http://localhost:5000
```

## 🎮 How It Works

### CLI Mode

When you run `python cleanup.py`, you'll see a friendly menu:

```
📧 Gmail Inbox Cleanup Assistant

📬 Inbox Status
Total emails: 1,234
Unread: 56

? What would you like to do?
> 🔍 Quick Scan - Find easy cleanup opportunities
  📊 Analyze top senders
  🗂️  Review by sender
  📝 Manage rules
  🧹 Bulk cleanup
  ⚙️  Settings
  👋 Exit
```

### Web UI Mode

A visual interface at `http://localhost:5000` with:
- Dashboard showing inbox stats
- Top senders list with one-click rule creation
- Email browser with search
- Rule management

## 🛡️ Safety First

**Safe Mode (Default):** Shows what would happen without actually changing anything.

**Live Mode:** Actually makes changes. Enable with:
```bash
python cleanup.py --live
```

**Nothing is permanently deleted!** Even when you "delete" emails, they go to Trash first (recoverable for 30 days).

## 📝 Creating Rules

Rules automatically organize your incoming emails. Example:

```
Rule: "Amazon"
When: Email is from amazon.com
Do: Add label "Shopping" and archive
```

Once synced to Gmail, this rule applies to ALL new emails automatically!

## 🔧 Setting Up Gmail Credentials

If you haven't set up the email skill yet:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable the Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download the JSON file
6. Save it as `~/.claude/.google/client_secret.json`

First time you run the tool, it will open a browser for you to log in.

## 📁 Project Structure

```
gmail-cleanup/
├── cleanup.py          # CLI entry point
├── web.py              # Web UI entry point
├── requirements.txt    # Python dependencies
├── data/               # Local data (rules, cache)
└── src/
    ├── gmail_cleanup/  # Core Gmail functionality
    │   ├── auth.py     # OAuth authentication
    │   ├── client.py   # Gmail API client
    │   ├── analyzer.py # Email analysis
    │   └── rules.py    # Rule management
    ├── cli/            # Command-line interface
    │   └── interactive.py
    └── web/            # Web interface
        ├── app.py
        └── templates/
```

## 🧠 ADHD-Friendly Design

This tool was designed with ADHD in mind:

- **Quick wins first** - Shows easiest cleanup opportunities at the top
- **Batch decisions** - Group similar emails to decide once, not 100 times
- **Clear progress** - Always know where you are and what's left
- **One-key actions** - Minimize clicks and decisions
- **Safe by default** - Can't accidentally delete everything

## 💡 Tips

1. **Start with Quick Scan** - It finds the easiest things to clean up
2. **Create rules for repeat senders** - One rule now saves work forever
3. **Use "older_than:1y"** - Great for finding emails you probably don't need
4. **Review large emails** - Often forgotten attachments taking up space

## 🔗 Integration with Email Skill

This tool complements your existing email skill:

- **Email Skill** = Sending and drafting emails
- **This Tool** = Organizing and cleaning up your inbox

Both share the same OAuth credentials, so setup is minimal.

---

Made with 💙 for inbox sanity

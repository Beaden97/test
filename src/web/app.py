"""
Simple Web UI for Gmail Cleanup

A visual way to browse and organize your emails.
Run this to start a local web server.
"""

import json
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

from ..gmail_cleanup import GmailAuth, GmailClient, EmailAnalyzer, RuleManager


app = Flask(__name__)
CORS(app)

# Global state (simple approach for single-user local tool)
_client = None
_auth = None
_rules = None


def get_client():
    """Get or create Gmail client."""
    global _client, _auth, _rules

    if _client is None:
        _auth = GmailAuth()
        service = _auth.get_service()
        _client = GmailClient(service, dry_run=True)  # Safe mode by default
        _rules = RuleManager(service)

    return _client


def get_rules():
    """Get rules manager."""
    get_client()  # Ensure initialized
    return _rules


@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Get connection status."""
    try:
        auth = GmailAuth()
        return jsonify({
            'authenticated': auth.is_authenticated(),
            'status': auth.get_status()
        })
    except Exception as e:
        return jsonify({'authenticated': False, 'error': str(e)})


@app.route('/api/inbox/stats')
def api_inbox_stats():
    """Get inbox statistics."""
    try:
        client = get_client()
        stats = client.get_inbox_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/emails')
def api_emails():
    """Get emails with optional search."""
    try:
        client = get_client()
        query = request.args.get('q', 'in:inbox')
        limit = int(request.args.get('limit', 50))

        emails = client.search_emails(query, max_results=limit)

        return jsonify({
            'emails': [
                {
                    'id': e.id,
                    'subject': e.subject,
                    'sender': e.sender,
                    'sender_email': e.sender_email,
                    'date': e.date.isoformat(),
                    'snippet': e.snippet,
                    'is_unread': e.is_unread,
                    'size_bytes': e.size_bytes,
                }
                for e in emails
            ],
            'count': len(emails)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze/senders')
def api_analyze_senders():
    """Analyze top senders."""
    try:
        client = get_client()
        limit = int(request.args.get('limit', 500))

        emails = client.search_emails('in:inbox', max_results=limit)
        analyzer = EmailAnalyzer(emails)
        analyzer.analyze()

        top_senders = analyzer.get_top_senders(20)

        return jsonify({
            'senders': [
                {
                    'email': s.email,
                    'name': s.name,
                    'count': s.total_count,
                    'unread': s.unread_count,
                    'size_mb': round(s.size_mb, 2),
                    'sample_subjects': s.sample_subjects,
                }
                for s in top_senders
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze/suggestions')
def api_suggestions():
    """Get cleanup suggestions."""
    try:
        client = get_client()

        emails = client.search_emails('in:inbox', max_results=500)
        analyzer = EmailAnalyzer(emails)
        analyzer.analyze()

        suggestions = analyzer.get_cleanup_suggestions()

        return jsonify({
            'suggestions': [
                {
                    'category': s.category,
                    'description': s.description,
                    'email_count': len(s.email_ids),
                    'size_mb': round(s.estimated_space_mb, 2),
                    'priority': s.priority,
                    'action': s.action,
                }
                for s in suggestions
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rules')
def api_rules():
    """Get all rules."""
    try:
        rules = get_rules()
        return jsonify({
            'rules': [
                {
                    'name': r.name,
                    'from_email': r.from_email,
                    'subject_contains': r.subject_contains,
                    'archive': r.archive,
                    'add_label': r.add_label,
                    'mark_read': r.mark_read,
                    'synced': r.gmail_filter_id is not None,
                }
                for r in rules.list_rules()
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/labels')
def api_labels():
    """Get all labels."""
    try:
        client = get_client()
        labels = client.get_labels()
        return jsonify({
            'labels': [
                {
                    'id': l.id,
                    'name': l.name,
                    'type': l.type,
                    'total': l.messages_total,
                    'unread': l.messages_unread,
                }
                for l in labels
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/emails/archive', methods=['POST'])
def api_archive():
    """Archive emails."""
    try:
        client = get_client()
        data = request.json
        email_ids = data.get('email_ids', [])

        if not email_ids:
            return jsonify({'error': 'No email IDs provided'}), 400

        count = client.archive_emails(email_ids)
        return jsonify({'archived': count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mode', methods=['GET', 'POST'])
def api_mode():
    """Get or set dry-run mode."""
    global _client

    if request.method == 'POST':
        data = request.json
        dry_run = data.get('dry_run', True)
        if _client:
            _client.dry_run = dry_run
        return jsonify({'dry_run': dry_run})

    return jsonify({'dry_run': _client.dry_run if _client else True})


def run_server(host='127.0.0.1', port=5000, debug=False):
    """Start the web server."""
    print(f"\n🌐 Starting Gmail Cleanup Web UI")
    print(f"   Open http://{host}:{port} in your browser\n")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server(debug=True)

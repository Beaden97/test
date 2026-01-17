"""
Gmail Cleanup Web API

A RESTful API for managing Gmail inbox cleanup.
Includes versioned endpoints, error handling, rate limiting, and caching.
"""

from flask import Flask, Blueprint, render_template, request, redirect
from flask_cors import CORS

from ..gmail_cleanup import GmailAuth, GmailClient, EmailAnalyzer, RuleManager
from ..gmail_cleanup.rules import Rule
from .errors import handle_errors, success_response, APIError, ErrorCode
from .validation import validate_query, validate_body, Schema
from .rate_limit import rate_limit, add_rate_limit_headers
from .cache import cache, cached, invalidate_cache


app = Flask(__name__)
CORS(app, origins=['http://localhost:5000', 'http://127.0.0.1:5000', 'http://localhost:3000', 'http://127.0.0.1:3000'])

# API v1 Blueprint
api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

# Global state (single-user local tool)
_client = None
_auth = None
_rules = None


def get_client():
    """Get or create Gmail client."""
    global _client, _auth, _rules

    if _client is None:
        _auth = GmailAuth()
        service = _auth.get_service()
        _client = GmailClient(service, dry_run=True)
        _rules = RuleManager(service)

    return _client


def get_rules():
    """Get rules manager."""
    get_client()
    return _rules


def serialize_email(e):
    """Serialize email to dict."""
    return {
        'id': e.id,
        'subject': e.subject,
        'sender': e.sender,
        'sender_email': e.sender_email,
        'date': e.date.isoformat(),
        'snippet': e.snippet,
        'is_unread': e.is_unread,
        'size_bytes': e.size_bytes,
    }


def serialize_sender(s):
    """Serialize sender stats to dict."""
    return {
        'email': s.email,
        'name': s.name,
        'count': s.total_count,
        'unread': s.unread_count,
        'size_mb': round(s.size_mb, 2),
        'sample_subjects': s.sample_subjects,
    }


def serialize_rule(r):
    """Serialize rule to dict."""
    return {
        'name': r.name,
        'from_email': r.from_email,
        'subject_contains': r.subject_contains,
        'archive': r.archive,
        'add_label': r.add_label,
        'mark_read': r.mark_read,
        'synced': r.gmail_filter_id is not None,
    }


# ============================================================================
# API v1 Endpoints
# ============================================================================

@api_v1.route('/health')
def health():
    """Health check endpoint."""
    return success_response({
        'status': 'healthy',
        'version': '1.0.0'
    })


@api_v1.route('/status')
@handle_errors
def api_status():
    """Get connection status."""
    auth = GmailAuth()
    return success_response({
        'authenticated': auth.is_authenticated(),
        'status': auth.get_status()
    })


@api_v1.route('/inbox/stats')
@handle_errors
@cached(ttl_seconds=60)
def api_inbox_stats():
    """Get inbox statistics."""
    client = get_client()
    stats = client.get_inbox_stats()
    return success_response(stats)


@api_v1.route('/emails')
@handle_errors
@validate_query(
    q=Schema.string(default='in:inbox'),
    limit=Schema.integer(min_val=1, max_val=500, default=50)
)
def api_emails(validated):
    """Get emails with optional search."""
    client = get_client()
    emails = client.search_emails(validated['q'], max_results=validated['limit'])

    return success_response(
        data={'emails': [serialize_email(e) for e in emails]},
        meta={'count': len(emails), 'query': validated['q'], 'limit': validated['limit']}
    )


@api_v1.route('/analyze/senders')
@handle_errors
@cached(ttl_seconds=300)
@validate_query(
    limit=Schema.integer(min_val=1, max_val=1000, default=500)
)
def api_analyze_senders(validated):
    """Analyze top senders."""
    client = get_client()
    emails = client.search_emails('in:inbox', max_results=validated['limit'])
    analyzer = EmailAnalyzer(emails)
    analyzer.analyze()

    return success_response({
        'senders': [serialize_sender(s) for s in analyzer.get_top_senders(20)]
    })


@api_v1.route('/analyze/suggestions')
@handle_errors
@cached(ttl_seconds=300)
def api_suggestions():
    """Get cleanup suggestions."""
    client = get_client()
    emails = client.search_emails('in:inbox', max_results=500)
    analyzer = EmailAnalyzer(emails)
    analyzer.analyze()

    suggestions = analyzer.get_cleanup_suggestions()

    return success_response({
        'suggestions': [
            {
                'category': s.category,
                'description': s.description,
                'email_count': len(s.email_ids),
                'email_ids': s.email_ids,
                'size_mb': round(s.estimated_space_mb, 2),
                'priority': s.priority,
                'action': s.action,
            }
            for s in suggestions
        ]
    })


@api_v1.route('/rules')
@handle_errors
def api_rules():
    """Get all rules."""
    rules = get_rules()
    return success_response({
        'rules': [serialize_rule(r) for r in rules.list_rules()]
    })


@api_v1.route('/rules', methods=['POST'])
@handle_errors
@rate_limit(limit=10, window=60)
@validate_body(
    name=Schema.string(min_len=1, max_len=100, required=True),
    from_email=Schema.string(max_len=255),
    subject_contains=Schema.string(max_len=255),
    archive=Schema.boolean(default=False),
    add_label=Schema.string(max_len=100),
    mark_read=Schema.boolean(default=False)
)
def create_rule(validated):
    """Create a new rule."""
    rules = get_rules()

    rule = Rule(
        name=validated['name'],
        from_email=validated.get('from_email'),
        subject_contains=validated.get('subject_contains'),
        archive=validated.get('archive', False),
        add_label=validated.get('add_label'),
        mark_read=validated.get('mark_read', False)
    )

    rules.create_rule(rule)
    invalidate_cache('api_rules')

    return success_response({'rule': serialize_rule(rule)})


@api_v1.route('/rules/<rule_name>', methods=['DELETE'])
@handle_errors
@rate_limit(limit=10, window=60)
def delete_rule(rule_name):
    """Delete a rule by name."""
    rules = get_rules()

    if not rules.delete_rule(rule_name):
        raise APIError(
            message=f"Rule '{rule_name}' not found",
            code=ErrorCode.NOT_FOUND,
            status_code=404
        )

    invalidate_cache('api_rules')
    return success_response({'deleted': rule_name})


@api_v1.route('/rules/<rule_name>/sync', methods=['POST'])
@handle_errors
@rate_limit(limit=5, window=60)
def sync_rule(rule_name):
    """Sync a rule to Gmail as a filter."""
    rules = get_rules()

    rule = next((r for r in rules.list_rules() if r.name == rule_name), None)
    if not rule:
        raise APIError(
            message=f"Rule '{rule_name}' not found",
            code=ErrorCode.NOT_FOUND,
            status_code=404
        )

    if not rules.sync_to_gmail(rule):
        raise APIError(
            message="Failed to sync rule to Gmail",
            code=ErrorCode.GMAIL_ERROR,
            status_code=500
        )

    return success_response({'synced': True, 'filter_id': rule.gmail_filter_id})


@api_v1.route('/labels')
@handle_errors
@cached(ttl_seconds=300)
def api_labels():
    """Get all labels."""
    client = get_client()
    labels = client.get_labels()
    return success_response({
        'labels': [
            {
                'id': label.id,
                'name': label.name,
                'type': label.type,
                'total': label.messages_total,
                'unread': label.messages_unread,
            }
            for label in labels
        ]
    })


@api_v1.route('/emails/archive', methods=['POST'])
@handle_errors
@rate_limit(limit=30, window=60)
@validate_body(
    email_ids=Schema.list_of('string', min_len=1, max_len=100, required=True)
)
def api_archive(validated):
    """Archive emails."""
    client = get_client()
    count = client.archive_emails(validated['email_ids'])
    invalidate_cache()  # Invalidate all cache after action
    return success_response({'archived': count})


@api_v1.route('/emails/trash', methods=['POST'])
@handle_errors
@rate_limit(limit=20, window=60)
@validate_body(
    email_ids=Schema.list_of('string', min_len=1, max_len=100, required=True)
)
def api_trash(validated):
    """Move emails to trash."""
    client = get_client()
    count = client.move_to_trash(validated['email_ids'])
    invalidate_cache()
    return success_response({'trashed': count})


@api_v1.route('/mode', methods=['GET'])
@handle_errors
def get_mode():
    """Get current dry-run mode."""
    return success_response({'dry_run': _client.dry_run if _client else True})


@api_v1.route('/mode', methods=['POST'])
@handle_errors
@rate_limit(limit=5, window=60)
@validate_body(
    dry_run=Schema.boolean(required=True),
    confirm=Schema.boolean(default=False)
)
def set_mode(validated):
    """Set dry-run mode (requires confirmation to disable)."""
    global _client

    if not validated['dry_run'] and not validated.get('confirm'):
        raise APIError(
            message="Must confirm to disable dry-run mode",
            code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details={"confirm": "Set to true to confirm disabling dry-run"}
        )

    if _client:
        _client.dry_run = validated['dry_run']

    return success_response({'dry_run': validated['dry_run']})


@api_v1.route('/cache/clear', methods=['POST'])
@handle_errors
@rate_limit(limit=5, window=60)
def clear_cache():
    """Clear the API cache."""
    invalidate_cache()
    return success_response({'cleared': True})


# ============================================================================
# Register Blueprint and Legacy Routes
# ============================================================================

app.register_blueprint(api_v1)


# Legacy route redirects (backwards compatibility)
@app.route('/api/status')
def legacy_status():
    return redirect('/api/v1/status', code=301)


@app.route('/api/inbox/stats')
def legacy_inbox_stats():
    return redirect('/api/v1/inbox/stats', code=301)


@app.route('/api/emails')
def legacy_emails():
    return redirect(f'/api/v1/emails?{request.query_string.decode()}', code=301)


@app.route('/api/analyze/senders')
def legacy_analyze_senders():
    return redirect(f'/api/v1/analyze/senders?{request.query_string.decode()}', code=301)


@app.route('/api/analyze/suggestions')
def legacy_suggestions():
    return redirect('/api/v1/analyze/suggestions', code=301)


@app.route('/api/rules')
def legacy_rules():
    return redirect('/api/v1/rules', code=301)


@app.route('/api/labels')
def legacy_labels():
    return redirect('/api/v1/labels', code=301)


# Add rate limit headers to all responses
@app.after_request
def after_request(response):
    response = add_rate_limit_headers(response)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response


# Main page (serves existing template)
@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


def run_server(host='127.0.0.1', port=5000, debug=False):
    """Start the web server."""
    print(f"\n🌐 Starting Gmail Cleanup Web API")
    print(f"   API: http://{host}:{port}/api/v1/")
    print(f"   Web UI: http://{host}:{port}/\n")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server(debug=True)

/**
 * API client for Gmail Cleanup Flask backend
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:5000/api/v1';

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  meta?: Record<string, unknown>;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

export interface Email {
  id: string;
  subject: string;
  sender: string;
  sender_email: string;
  date: string;
  snippet: string;
  is_unread: boolean;
  size_bytes: number;
}

export interface Sender {
  email: string;
  name: string;
  count: number;
  unread: number;
  size_mb: number;
  sample_subjects: string[];
}

export interface Suggestion {
  category: string;
  description: string;
  email_count: number;
  email_ids: string[];
  size_mb: number;
  priority: number;
  action: string;
}

export interface Rule {
  name: string;
  from_email: string | null;
  subject_contains: string | null;
  archive: boolean;
  add_label: string | null;
  mark_read: boolean;
  synced: boolean;
}

export interface InboxStats {
  total_inbox: number;
  unread_inbox: number;
  total_all: number;
}

export interface Label {
  id: string;
  name: string;
  type: string;
  total: number;
  unread: number;
}

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const url = `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  const data = await response.json();
  return data;
}

export const api = {
  // Health & Status
  async getHealth() {
    return fetchApi<{ status: string; version: string }>('/health');
  },

  async getStatus() {
    return fetchApi<{ authenticated: boolean; status: string }>('/status');
  },

  // Inbox
  async getInboxStats() {
    return fetchApi<InboxStats>('/inbox/stats');
  },

  async getEmails(query = 'in:inbox', limit = 50) {
    return fetchApi<{ emails: Email[] }>(
      `/emails?q=${encodeURIComponent(query)}&limit=${limit}`
    );
  },

  // Analysis
  async getTopSenders(limit = 500) {
    return fetchApi<{ senders: Sender[] }>(`/analyze/senders?limit=${limit}`);
  },

  async getSuggestions() {
    return fetchApi<{ suggestions: Suggestion[] }>('/analyze/suggestions');
  },

  // Rules
  async getRules() {
    return fetchApi<{ rules: Rule[] }>('/rules');
  },

  async createRule(rule: Partial<Rule>) {
    return fetchApi<{ rule: Rule }>('/rules', {
      method: 'POST',
      body: JSON.stringify(rule),
    });
  },

  async deleteRule(name: string) {
    return fetchApi<{ deleted: string }>(`/rules/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    });
  },

  async syncRule(name: string) {
    return fetchApi<{ synced: boolean; filter_id: string }>(
      `/rules/${encodeURIComponent(name)}/sync`,
      { method: 'POST' }
    );
  },

  // Labels
  async getLabels() {
    return fetchApi<{ labels: Label[] }>('/labels');
  },

  // Actions
  async archiveEmails(emailIds: string[]) {
    return fetchApi<{ archived: number }>('/emails/archive', {
      method: 'POST',
      body: JSON.stringify({ email_ids: emailIds }),
    });
  },

  async trashEmails(emailIds: string[]) {
    return fetchApi<{ trashed: number }>('/emails/trash', {
      method: 'POST',
      body: JSON.stringify({ email_ids: emailIds }),
    });
  },

  // Mode
  async getMode() {
    return fetchApi<{ dry_run: boolean }>('/mode');
  },

  async setMode(dryRun: boolean, confirm = false) {
    return fetchApi<{ dry_run: boolean }>('/mode', {
      method: 'POST',
      body: JSON.stringify({ dry_run: dryRun, confirm }),
    });
  },

  // Cache
  async clearCache() {
    return fetchApi<{ cleared: boolean }>('/cache/clear', { method: 'POST' });
  },
};

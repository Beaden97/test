import { Suspense } from 'react';
import { api } from '@/lib/api';

// Server Component - fetches data on server
async function InboxStats() {
  const response = await api.getInboxStats();

  if (!response.success || !response.data) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-600">Failed to load inbox stats</p>
      </div>
    );
  }

  const stats = response.data;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-sm font-medium text-gray-500">Total Inbox</div>
        <div className="text-3xl font-bold text-gray-900 mt-1">
          {stats.total_inbox?.toLocaleString() ?? 0}
        </div>
      </div>
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-sm font-medium text-gray-500">Unread</div>
        <div className="text-3xl font-bold text-yellow-600 mt-1">
          {stats.unread_inbox?.toLocaleString() ?? 0}
        </div>
      </div>
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-sm font-medium text-gray-500">Total All Mail</div>
        <div className="text-3xl font-bold text-gray-900 mt-1">
          {stats.total_all?.toLocaleString() ?? 0}
        </div>
      </div>
    </div>
  );
}

async function CleanupSuggestions() {
  const response = await api.getSuggestions();

  if (!response.success || !response.data) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-yellow-700">No suggestions available</p>
      </div>
    );
  }

  const suggestions = response.data.suggestions;

  if (suggestions.length === 0) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <p className="text-green-700">✨ Your inbox looks clean!</p>
      </div>
    );
  }

  const priorityColors: Record<number, string> = {
    1: 'bg-red-100 text-red-800',
    2: 'bg-yellow-100 text-yellow-800',
    3: 'bg-green-100 text-green-800',
  };

  return (
    <div className="space-y-3">
      {suggestions.slice(0, 5).map((s, i) => (
        <div key={i} className="bg-white rounded-lg shadow p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className={`px-2 py-1 rounded text-xs font-medium ${priorityColors[s.priority] || 'bg-gray-100'}`}>
              P{s.priority}
            </span>
            <div>
              <div className="font-medium text-gray-900">{s.description}</div>
              <div className="text-sm text-gray-500">
                {s.email_count} emails · {s.size_mb} MB
              </div>
            </div>
          </div>
          <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition">
            {s.action === 'archive' ? 'Archive' : 'Review'}
          </button>
        </div>
      ))}
    </div>
  );
}

async function TopSenders() {
  const response = await api.getTopSenders(100);

  if (!response.success || !response.data) {
    return null;
  }

  const senders = response.data.senders.slice(0, 5);

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="px-4 py-3 border-b border-gray-200">
        <h3 className="font-semibold text-gray-900">Top Senders</h3>
      </div>
      <div className="divide-y divide-gray-100">
        {senders.map((s, i) => (
          <div key={i} className="px-4 py-3 flex items-center justify-between">
            <div>
              <div className="font-medium text-gray-900">{s.name}</div>
              <div className="text-sm text-gray-500">{s.email}</div>
            </div>
            <div className="text-right">
              <div className="font-semibold text-gray-900">{s.count}</div>
              <div className="text-xs text-gray-500">{s.size_mb} MB</div>
            </div>
          </div>
        ))}
      </div>
      <a href="/senders" className="block px-4 py-3 text-center text-blue-600 hover:bg-gray-50 text-sm">
        View all senders →
      </a>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="h-24 bg-gray-200 rounded-lg"></div>
    </div>
  );
}

export default function Dashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Dashboard</h2>
        <Suspense fallback={<LoadingSkeleton />}>
          <InboxStats />
        </Suspense>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Cleanup Suggestions</h3>
          <Suspense fallback={<LoadingSkeleton />}>
            <CleanupSuggestions />
          </Suspense>
        </div>

        <div>
          <Suspense fallback={<LoadingSkeleton />}>
            <TopSenders />
          </Suspense>
        </div>
      </div>
    </div>
  );
}

// Force dynamic rendering since we need fresh data
export const dynamic = 'force-dynamic';

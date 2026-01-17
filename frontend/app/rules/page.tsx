import { Suspense } from 'react';
import { api } from '@/lib/api';

async function RulesList() {
  const response = await api.getRules();

  if (!response.success || !response.data) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-600">Failed to load rules</p>
      </div>
    );
  }

  const rules = response.data.rules;

  if (rules.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <div className="text-4xl mb-4">📝</div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">No rules yet</h3>
        <p className="text-gray-500 mb-4">
          Create rules to automatically organize incoming emails
        </p>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          Create Your First Rule
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {rules.map((rule, i) => (
        <div key={i} className="bg-white rounded-lg shadow p-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-gray-900">{rule.name}</h3>
                {rule.synced ? (
                  <span className="px-2 py-0.5 text-xs bg-green-100 text-green-800 rounded">
                    Synced to Gmail
                  </span>
                ) : (
                  <span className="px-2 py-0.5 text-xs bg-yellow-100 text-yellow-800 rounded">
                    Local only
                  </span>
                )}
              </div>

              <div className="mt-2 text-sm text-gray-600 space-y-1">
                {rule.from_email && (
                  <div>
                    <span className="text-gray-400">From:</span> {rule.from_email}
                  </div>
                )}
                {rule.subject_contains && (
                  <div>
                    <span className="text-gray-400">Subject contains:</span> {rule.subject_contains}
                  </div>
                )}
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                {rule.archive && (
                  <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                    📥 Archive
                  </span>
                )}
                {rule.add_label && (
                  <span className="px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded">
                    🏷️ Label: {rule.add_label}
                  </span>
                )}
                {rule.mark_read && (
                  <span className="px-2 py-1 text-xs bg-gray-100 text-gray-800 rounded">
                    ✓ Mark as read
                  </span>
                )}
              </div>
            </div>

            <div className="flex gap-2">
              {!rule.synced && (
                <button className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700">
                  Sync to Gmail
                </button>
              )}
              <button className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200">
                Delete
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      {[...Array(3)].map((_, i) => (
        <div key={i} className="h-32 bg-gray-200 rounded-lg"></div>
      ))}
    </div>
  );
}

export default function RulesPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Email Rules</h2>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          + New Rule
        </button>
      </div>

      <Suspense fallback={<LoadingSkeleton />}>
        <RulesList />
      </Suspense>
    </div>
  );
}

export const dynamic = 'force-dynamic';

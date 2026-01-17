import { Suspense } from 'react';
import { api } from '@/lib/api';

async function SendersList() {
  const response = await api.getTopSenders(500);

  if (!response.success || !response.data) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-600">Failed to load senders</p>
      </div>
    );
  }

  const senders = response.data.senders;

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Sender
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Emails
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Unread
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Size
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {senders.map((sender, i) => (
            <tr key={i} className="hover:bg-gray-50">
              <td className="px-6 py-4">
                <div className="font-medium text-gray-900">{sender.name}</div>
                <div className="text-sm text-gray-500">{sender.email}</div>
                {sender.sample_subjects.length > 0 && (
                  <div className="text-xs text-gray-400 mt-1 truncate max-w-md">
                    {sender.sample_subjects[0]}
                  </div>
                )}
              </td>
              <td className="px-6 py-4 text-right text-sm font-semibold text-gray-900">
                {sender.count}
              </td>
              <td className="px-6 py-4 text-right text-sm">
                {sender.unread > 0 ? (
                  <span className="text-yellow-600 font-medium">{sender.unread}</span>
                ) : (
                  <span className="text-gray-400">-</span>
                )}
              </td>
              <td className="px-6 py-4 text-right text-sm text-gray-500">
                {sender.size_mb} MB
              </td>
              <td className="px-6 py-4 text-right">
                <div className="flex gap-2 justify-end">
                  <button className="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700">
                    Create Rule
                  </button>
                  <button className="px-3 py-1 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300">
                    Archive All
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="h-16 bg-gray-200 rounded-lg"></div>
      ))}
    </div>
  );
}

export default function SendersPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Top Senders</h2>
        <div className="text-sm text-gray-500">
          Sorted by email count
        </div>
      </div>

      <Suspense fallback={<LoadingSkeleton />}>
        <SendersList />
      </Suspense>
    </div>
  );
}

export const dynamic = 'force-dynamic';

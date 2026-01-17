import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Gmail Cleanup',
  description: 'Clean up your Gmail inbox efficiently',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">
        <nav className="bg-white border-b border-gray-200 px-4 py-3">
          <div className="max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-2xl">📧</span>
              <h1 className="text-xl font-semibold text-gray-900">Gmail Cleanup</h1>
            </div>
            <div className="flex items-center gap-4">
              <a href="/" className="text-gray-600 hover:text-gray-900">Dashboard</a>
              <a href="/senders" className="text-gray-600 hover:text-gray-900">Senders</a>
              <a href="/rules" className="text-gray-600 hover:text-gray-900">Rules</a>
            </div>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 py-6">
          {children}
        </main>
      </body>
    </html>
  );
}

import { useQuery } from '@tanstack/react-query'
import { automationApi } from '../api/resources.js'
import EmptyState from '../components/EmptyState.jsx'

export default function ReportsPage() {
  const { data, isLoading } = useQuery({ queryKey: ['reports'], queryFn: automationApi.reports })

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Generated Reports</h1>
      {isLoading ? (
        <div className="text-sm text-slate-500">Loading…</div>
      ) : data?.length === 0 ? (
        <EmptyState
          title="No reports yet"
          hint="Weekly summaries and expiry alerts will appear here when the scheduler runs"
        />
      ) : (
        <div className="space-y-3">
          {data?.map((r) => (
            <div key={r.id} className="card">
              <div className="flex justify-between items-baseline">
                <h2 className="font-semibold">{r.title}</h2>
                <span className="text-xs text-slate-500">{new Date(r.created_at).toLocaleString()}</span>
              </div>
              <span className="badge bg-indigo-100 text-indigo-800 mt-1 inline-block">{r.type}</span>
              <pre className="mt-3 whitespace-pre-wrap text-sm text-slate-700">{r.content_md}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

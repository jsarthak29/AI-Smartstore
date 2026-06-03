import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { automationApi } from '../api/resources.js'
import EmptyState from '../components/EmptyState.jsx'
import { useAuthStore } from '../store/authStore.js'

const JOBS = ['low_stock_agent', 'weekly_summary_agent', 'expiry_agent']

export default function AutomationLogsPage() {
  const qc = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const isAdmin = user?.role === 'admin'
  const { data: logs, isLoading } = useQuery({ queryKey: ['automation-logs'], queryFn: automationApi.logs })

  const trigger = useMutation({
    mutationFn: automationApi.runNow,
    onSuccess: (_d, jobName) => {
      toast.success(`Ran ${jobName}`)
      qc.invalidateQueries({ queryKey: ['automation-logs'] })
      qc.invalidateQueries({ queryKey: ['pos'] })
      qc.invalidateQueries({ queryKey: ['reports'] })
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Automation Logs</h1>
        {isAdmin && (
          <div className="space-x-2">
            {JOBS.map((j) => (
              <button key={j} className="btn-secondary text-xs" onClick={() => trigger.mutate(j)}>Run {j}</button>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        {isLoading ? (
          <div className="text-sm text-slate-500">Loading…</div>
        ) : logs?.length === 0 ? (
          <EmptyState
            title="No automation runs yet"
            hint={isAdmin ? "Use the buttons above to trigger a run, or wait for the daily cron" : "Logs will appear once the scheduler has run"}
          />
        ) : (
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="py-2 px-3">When</th>
                <th className="py-2 px-3">Job</th>
                <th className="py-2 px-3">Status</th>
                <th className="py-2 px-3">Outcome</th>
              </tr>
            </thead>
            <tbody>
              {logs?.map((l) => (
                <tr key={l.id} className="border-b border-slate-100 align-top">
                  <td className="py-2 px-3 text-xs whitespace-nowrap">{new Date(l.ts).toLocaleString()}</td>
                  <td className="py-2 px-3 font-mono text-xs">{l.job_name}</td>
                  <td className="py-2 px-3"><span className={`badge ${l.status === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>{l.status}</span></td>
                  <td className="py-2 px-3 text-xs font-mono"><pre className="whitespace-pre-wrap">{JSON.stringify(l.outcome, null, 2)}</pre></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

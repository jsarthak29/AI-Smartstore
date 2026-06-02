import { useQuery } from '@tanstack/react-query'
import { automationApi, productsApi } from '../api/resources.js'
import StockBadge from '../components/StockBadge.jsx'
import { SkeletonCard } from '../components/Skeleton.jsx'
import EmptyState from '../components/EmptyState.jsx'
import { Link } from 'react-router-dom'

function Card({ label, value, accent }) {
  return (
    <div className="card">
      <div className="text-xs uppercase tracking-wider text-slate-500">{label}</div>
      <div className={`text-3xl font-semibold mt-1 ${accent || 'text-slate-800'}`}>{value}</div>
    </div>
  )
}

export default function DashboardPage() {
  const { data: summary, isLoading } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: automationApi.summary,
  })
  const { data: lowStock } = useQuery({
    queryKey: ['products', { status: 'low' }],
    queryFn: () => productsApi.list({ status: 'critical', page_size: 100 }),
  })

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {isLoading || !summary ? (
          <>
            <SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard />
          </>
        ) : (
          <>
            <Card label="Total Products" value={summary.total_products} />
            <Card label="Low Stock Alerts" value={summary.low_stock_count} accent={summary.low_stock_count > 0 ? 'text-amber-600' : ''} />
            <Card label="Expired Items" value={summary.expired_count} accent={summary.expired_count > 0 ? 'text-red-600' : ''} />
            <Card label="Pending POs" value={summary.pending_po_count} />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card">
          <h2 className="font-semibold mb-3">Top 5 Movers (last 30 days)</h2>
          {(!summary || summary.top_movers.length === 0)
            ? <EmptyState title="No sales activity yet" hint="Movements will appear as stock leaves the warehouse" />
            : (
              <ul className="divide-y divide-slate-100">
                {summary.top_movers.map((m) => (
                  <li key={m.id} className="flex justify-between py-2 text-sm">
                    <Link to={`/products/${m.id}`} className="hover:text-brand-600">{m.name} <span className="text-slate-400">({m.sku})</span></Link>
                    <span className="font-medium">{m.volume} units</span>
                  </li>
                ))}
              </ul>
            )}
        </div>

        <div className="card">
          <h2 className="font-semibold mb-3">Critical / Out of Stock</h2>
          {(!lowStock || lowStock.items.length === 0)
            ? <EmptyState title="No critical items 🎉" />
            : (
              <ul className="divide-y divide-slate-100">
                {lowStock.items.slice(0, 8).map((p) => (
                  <li key={p.id} className="flex justify-between items-center py-2 text-sm">
                    <Link to={`/products/${p.id}`} className="hover:text-brand-600">{p.name}</Link>
                    <div className="flex items-center gap-2">
                      <span className="text-slate-500">{p.stock} left</span>
                      <StockBadge status={p.stock_status} />
                    </div>
                  </li>
                ))}
              </ul>
            )}
        </div>
      </div>
    </div>
  )
}

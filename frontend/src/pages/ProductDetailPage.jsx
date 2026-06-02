import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { productsApi } from '../api/resources.js'
import StockBadge from '../components/StockBadge.jsx'

export default function ProductDetailPage() {
  const { id } = useParams()
  const productId = Number(id)
  const { data: product } = useQuery({ queryKey: ['product', productId], queryFn: () => productsApi.get(productId) })
  const { data: forecast } = useQuery({ queryKey: ['forecast', productId], queryFn: () => productsApi.forecast(productId) })

  if (!product) return <div>Loading…</div>

  return (
    <div className="space-y-4">
      <Link to="/products" className="text-sm text-brand-600">← Back to products</Link>
      <div className="card">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-semibold">{product.name}</h1>
            <div className="text-sm text-slate-500 font-mono">{product.sku}</div>
          </div>
          <StockBadge status={product.stock_status} />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4 text-sm">
          <div><div className="text-slate-500">Category</div><div className="font-medium">{product.category}</div></div>
          <div><div className="text-slate-500">Stock</div><div className="font-medium">{product.stock}</div></div>
          <div><div className="text-slate-500">Unit price</div><div className="font-medium">₹{Number(product.unit_price).toFixed(2)}</div></div>
          <div><div className="text-slate-500">Reorder ≤</div><div className="font-medium">{product.reorder_threshold}</div></div>
          <div><div className="text-slate-500">Expiry</div><div className="font-medium">{product.expiry_date || '—'}</div></div>
        </div>
      </div>

      <div className="card">
        <h2 className="font-semibold mb-3">7-day Demand Forecast</h2>
        {forecast ? (
          <>
            <p className="text-xs text-slate-500 mb-2">Method: {forecast.method} · History: {forecast.history_days_used} days</p>
            <div style={{ width: '100%', height: 280 }}>
              <ResponsiveContainer>
                <LineChart data={forecast.points} margin={{ left: 10, right: 20, top: 10, bottom: 30 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" label={{ value: 'Date', position: 'insideBottom', offset: -5 }} />
                  <YAxis label={{ value: 'Predicted units / day', angle: -90, position: 'insideLeft' }} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="predicted_demand" stroke="#2563eb" strokeWidth={2} name="Predicted demand" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </>
        ) : (
          <p className="text-sm text-slate-500">Loading forecast…</p>
        )}
      </div>
    </div>
  )
}

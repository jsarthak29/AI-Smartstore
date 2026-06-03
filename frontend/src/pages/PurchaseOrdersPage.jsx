import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { posApi, productsApi, suppliersApi } from '../api/resources.js'
import EmptyState from '../components/EmptyState.jsx'
import { useAuthStore } from '../store/authStore.js'

const STATUS_NEXT = { draft: 'sent', sent: 'acknowledged', acknowledged: 'received' }
const STATUS_CLASS = {
  draft: 'bg-slate-200 text-slate-800',
  sent: 'bg-blue-100 text-blue-800',
  acknowledged: 'bg-amber-100 text-amber-800',
  received: 'bg-green-100 text-green-800',
}

function POForm({ suppliers, products, onCreated }) {
  const qc = useQueryClient()
  const [supplierId, setSupplierId] = useState('')
  const [lines, setLines] = useState([{ product_id: '', qty: 1 }])

  const create = useMutation({
    mutationFn: posApi.create,
    onSuccess: () => {
      toast.success('PO created (draft)')
      qc.invalidateQueries({ queryKey: ['pos'] })
      setLines([{ product_id: '', qty: 1 }])
      setSupplierId('')
      onCreated?.()
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  const addLine = () => setLines([...lines, { product_id: '', qty: 1 }])
  const updateLine = (i, k, v) => setLines(lines.map((l, idx) => idx === i ? { ...l, [k]: v } : l))
  const removeLine = (i) => setLines(lines.filter((_, idx) => idx !== i))

  const submit = (ev) => {
    ev.preventDefault()
    if (!supplierId) return toast.error('Choose a supplier')
    const validLines = lines.filter(l => l.product_id && Number(l.qty) > 0)
    if (validLines.length === 0) return toast.error('Add at least one line item')
    create.mutate({
      supplier_id: Number(supplierId),
      lines: validLines.map(l => ({ product_id: Number(l.product_id), qty: Number(l.qty) })),
    })
  }

  return (
    <form onSubmit={submit} className="card space-y-3">
      <h2 className="font-semibold">New Purchase Order</h2>
      <div>
        <label className="label">Supplier</label>
        <select className="input max-w-md" value={supplierId} onChange={(e) => setSupplierId(e.target.value)}>
          <option value="">— select —</option>
          {suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
        </select>
      </div>
      <div>
        <label className="label">Line items</label>
        <div className="space-y-2">
          {lines.map((l, i) => (
            <div key={i} className="flex gap-2 items-center">
              <select className="input flex-1" value={l.product_id} onChange={(e) => updateLine(i, 'product_id', e.target.value)}>
                <option value="">— product —</option>
                {products.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>)}
              </select>
              <input type="number" min="1" className="input w-24" value={l.qty} onChange={(e) => updateLine(i, 'qty', e.target.value)} />
              <button type="button" className="text-red-600 text-xs" onClick={() => removeLine(i)}>×</button>
            </div>
          ))}
          <button type="button" className="text-brand-600 text-xs" onClick={addLine}>+ Add line</button>
        </div>
      </div>
      <button className="btn-primary">Create draft PO</button>
    </form>
  )
}

export default function PurchaseOrdersPage() {
  const qc = useQueryClient()
  const user = useAuthStore((s) => s.user)
  const isAdmin = user?.role === 'admin'
  const [supplierFilter, setSupplierFilter] = useState('')

  const { data: pos, isLoading } = useQuery({
    queryKey: ['pos', { supplierFilter }],
    queryFn: () => posApi.list(supplierFilter ? { supplier_id: supplierFilter } : {}),
  })
  const { data: suppliers } = useQuery({ queryKey: ['suppliers'], queryFn: suppliersApi.list })
  const { data: products } = useQuery({
    queryKey: ['products-flat'],
    queryFn: () => productsApi.list({ page: 1, page_size: 100 }).then(d => d.items),
  })

  const advance = useMutation({
    mutationFn: ({ id, status }) => posApi.updateStatus(id, status),
    onSuccess: () => {
      toast.success('Status updated')
      qc.invalidateQueries({ queryKey: ['pos'] })
      qc.invalidateQueries({ queryKey: ['products'] })
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  const sendEmail = useMutation({
    mutationFn: posApi.sendEmail,
    onSuccess: (data) => toast.success(`Sent to ${data.sent_to || 'supplier'}`),
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Purchase Orders</h1>

      <POForm suppliers={suppliers || []} products={products || []} />

      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold">PO History</h2>
          <select className="input max-w-xs" value={supplierFilter} onChange={(e) => setSupplierFilter(e.target.value)}>
            <option value="">All suppliers</option>
            {(suppliers || []).map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
        {isLoading ? (
          <div className="text-sm text-slate-500">Loading…</div>
        ) : pos?.length === 0 ? (
          <EmptyState title="No purchase orders yet" hint="Create one above or wait for the low-stock agent" />
        ) : (
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="py-2 px-3">#</th>
                <th className="py-2 px-3">Supplier</th>
                <th className="py-2 px-3">Status</th>
                <th className="py-2 px-3 text-right">Total</th>
                <th className="py-2 px-3">Lines</th>
                <th className="py-2 px-3">Created</th>
                <th className="py-2 px-3"></th>
              </tr>
            </thead>
            <tbody>
              {pos?.map((po) => {
                const sup = (suppliers || []).find(s => s.id === po.supplier_id)
                const next = STATUS_NEXT[po.status]
                return (
                  <tr key={po.id} className="border-b border-slate-100">
                    <td className="py-2 px-3 font-mono text-xs">{po.id}</td>
                    <td className="py-2 px-3">{sup?.name || `#${po.supplier_id}`}</td>
                    <td className="py-2 px-3"><span className={`badge ${STATUS_CLASS[po.status]}`}>{po.status}</span></td>
                    <td className="py-2 px-3 text-right">₹{Number(po.total).toFixed(2)}</td>
                    <td className="py-2 px-3">{po.lines.length}</td>
                    <td className="py-2 px-3 text-xs">{new Date(po.created_at).toLocaleDateString()}</td>
                    <td className="py-2 px-3 text-right space-x-2">
                      {po.status === 'draft' && isAdmin && (
                        <button className="text-brand-600 text-xs" onClick={() => sendEmail.mutate(po.id)}>Send email</button>
                      )}
                      {next && (
                        <button className="text-brand-600 text-xs" onClick={() => advance.mutate({ id: po.id, status: next })}>→ {next}</button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

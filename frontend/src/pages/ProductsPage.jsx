import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { productsApi, suppliersApi } from '../api/resources.js'
import StockBadge from '../components/StockBadge.jsx'
import { SkeletonRow } from '../components/Skeleton.jsx'
import EmptyState from '../components/EmptyState.jsx'
import ProductFormModal from '../components/ProductFormModal.jsx'

export default function ProductsPage() {
  const qc = useQueryClient()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [status, setStatus] = useState('')
  const [modal, setModal] = useState({ open: false, product: null })

  const { data, isLoading } = useQuery({
    queryKey: ['products', { page, search, category, status }],
    queryFn: () => productsApi.list({ page, page_size: 20, q: search || undefined, category: category || undefined, status: status || undefined }),
  })
  const { data: suppliers } = useQuery({ queryKey: ['suppliers'], queryFn: suppliersApi.list })

  const remove = useMutation({
    mutationFn: productsApi.remove,
    onSuccess: () => {
      toast.success('Product archived')
      qc.invalidateQueries({ queryKey: ['products'] })
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Delete failed'),
  })

  const categories = data ? Array.from(new Set(data.items.map(p => p.category))) : []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Products</h1>
        <button onClick={() => setModal({ open: true, product: null })} className="btn-primary">+ Add product</button>
      </div>

      <div className="card flex flex-wrap gap-3">
        <input className="input max-w-xs" placeholder="Search SKU or name" value={search} onChange={(e) => setSearch(e.target.value)} />
        <select className="input max-w-xs" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select className="input max-w-xs" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All stock states</option>
          <option value="ok">OK</option>
          <option value="low">Low</option>
          <option value="critical">Critical</option>
          <option value="expired">Expired</option>
        </select>
      </div>

      <div className="card overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500 border-b border-slate-200">
              <th className="py-2 px-3">SKU</th>
              <th className="py-2 px-3">Name</th>
              <th className="py-2 px-3">Category</th>
              <th className="py-2 px-3 text-right">Stock</th>
              <th className="py-2 px-3 text-right">Price (₹)</th>
              <th className="py-2 px-3">Expiry</th>
              <th className="py-2 px-3">Status</th>
              <th className="py-2 px-3"></th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <>
                <SkeletonRow cols={8} /><SkeletonRow cols={8} /><SkeletonRow cols={8} />
              </>
            ) : data?.items.length === 0 ? (
              <tr><td colSpan={8}><EmptyState title="No products match your filters" /></td></tr>
            ) : (
              data?.items.map((p) => (
                <tr key={p.id} className="border-b border-slate-100">
                  <td className="py-2 px-3 font-mono text-xs">{p.sku}</td>
                  <td className="py-2 px-3"><Link to={`/products/${p.id}`} className="text-brand-600 hover:underline">{p.name}</Link></td>
                  <td className="py-2 px-3">{p.category}</td>
                  <td className="py-2 px-3 text-right">{p.stock}</td>
                  <td className="py-2 px-3 text-right">{Number(p.unit_price).toFixed(2)}</td>
                  <td className="py-2 px-3 text-xs">{p.expiry_date || '—'}</td>
                  <td className="py-2 px-3"><StockBadge status={p.stock_status} /></td>
                  <td className="py-2 px-3 text-right space-x-2">
                    <button className="text-brand-600 text-xs" onClick={() => setModal({ open: true, product: p })}>Edit</button>
                    <button className="text-red-600 text-xs" onClick={() => { if (confirm(`Archive ${p.name}?`)) remove.mutate(p.id) }}>Delete</button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {data && (
        <div className="flex justify-between items-center text-sm">
          <span>{data.total} items</span>
          <div className="space-x-2">
            <button className="btn-secondary" disabled={page === 1} onClick={() => setPage(p => p - 1)}>Prev</button>
            <span>Page {page}</span>
            <button className="btn-secondary" disabled={page * 20 >= data.total} onClick={() => setPage(p => p + 1)}>Next</button>
          </div>
        </div>
      )}

      {modal.open && (
        <ProductFormModal
          product={modal.product}
          suppliers={suppliers || []}
          onClose={() => setModal({ open: false, product: null })}
          onSaved={() => {
            setModal({ open: false, product: null })
            qc.invalidateQueries({ queryKey: ['products'] })
          }}
        />
      )}
    </div>
  )
}

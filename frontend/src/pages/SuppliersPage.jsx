import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { suppliersApi } from '../api/resources.js'
import EmptyState from '../components/EmptyState.jsx'

export default function SuppliersPage() {
  const qc = useQueryClient()
  const isAdmin = true  // auth disabled for demo
  const { data, isLoading } = useQuery({ queryKey: ['suppliers'], queryFn: suppliersApi.list })
  const [form, setForm] = useState({ name: '', email: '', categories: '', lead_time_days: 7 })
  const [errors, setErrors] = useState({})

  const create = useMutation({
    mutationFn: suppliersApi.create,
    onSuccess: () => {
      toast.success('Supplier added')
      qc.invalidateQueries({ queryKey: ['suppliers'] })
      setForm({ name: '', email: '', categories: '', lead_time_days: 7 })
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  const remove = useMutation({
    mutationFn: suppliersApi.remove,
    onSuccess: () => {
      toast.success('Supplier deleted')
      qc.invalidateQueries({ queryKey: ['suppliers'] })
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  const submit = (ev) => {
    ev.preventDefault()
    const e = {}
    if (!form.name) e.name = 'required'
    if (!form.email.includes('@')) e.email = 'invalid email'
    setErrors(e)
    if (Object.keys(e).length) return
    create.mutate({
      name: form.name,
      email: form.email,
      categories: form.categories.split(',').map(c => c.trim()).filter(Boolean),
      lead_time_days: Number(form.lead_time_days),
    })
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Suppliers</h1>

      {isAdmin && (
        <form onSubmit={submit} className="card grid grid-cols-1 sm:grid-cols-5 gap-3 items-end">
          <div className="sm:col-span-1">
            <label className="label">Name</label>
            <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            {errors.name && <p className="text-xs text-red-600">{errors.name}</p>}
          </div>
          <div className="sm:col-span-1">
            <label className="label">Email</label>
            <input className="input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            {errors.email && <p className="text-xs text-red-600">{errors.email}</p>}
          </div>
          <div className="sm:col-span-2">
            <label className="label">Categories (comma separated)</label>
            <input className="input" value={form.categories} onChange={(e) => setForm({ ...form, categories: e.target.value })} />
          </div>
          <div>
            <label className="label">Lead days</label>
            <input type="number" className="input" value={form.lead_time_days} onChange={(e) => setForm({ ...form, lead_time_days: e.target.value })} />
          </div>
          <div className="sm:col-span-5">
            <button className="btn-primary">+ Add supplier</button>
          </div>
        </form>
      )}

      <div className="card overflow-x-auto">
        {isLoading ? (
          <div className="text-sm text-slate-500">Loading…</div>
        ) : data?.length === 0 ? (
          <EmptyState title="No suppliers yet" />
        ) : (
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="py-2 px-3">Name</th>
                <th className="py-2 px-3">Email</th>
                <th className="py-2 px-3">Categories</th>
                <th className="py-2 px-3">Lead Time</th>
                <th className="py-2 px-3"></th>
              </tr>
            </thead>
            <tbody>
              {data?.map((s) => (
                <tr key={s.id} className="border-b border-slate-100">
                  <td className="py-2 px-3 font-medium">{s.name}</td>
                  <td className="py-2 px-3">{s.email}</td>
                  <td className="py-2 px-3">{(s.categories || []).join(', ')}</td>
                  <td className="py-2 px-3">{s.lead_time_days} days</td>
                  <td className="py-2 px-3 text-right">
                    {isAdmin && (
                      <button className="text-red-600 text-xs" onClick={() => { if (confirm(`Delete ${s.name}?`)) remove.mutate(s.id) }}>Delete</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

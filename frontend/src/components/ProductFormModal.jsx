import { useState } from 'react'
import toast from 'react-hot-toast'
import { productsApi } from '../api/resources.js'

export default function ProductFormModal({ product, suppliers, onClose, onSaved }) {
  const isEdit = !!product
  const [form, setForm] = useState({
    sku: product?.sku || '',
    name: product?.name || '',
    category: product?.category || '',
    unit_price: product?.unit_price ?? '',
    stock: product?.stock ?? 0,
    reorder_threshold: product?.reorder_threshold ?? 10,
    expiry_date: product?.expiry_date || '',
    preferred_supplier_id: product?.preferred_supplier_id ?? '',
  })
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)

  const change = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const validate = () => {
    const e = {}
    if (!isEdit && !form.sku) e.sku = 'SKU required'
    if (!form.name) e.name = 'Name required'
    if (!form.category) e.category = 'Category required'
    if (!form.unit_price || Number(form.unit_price) <= 0) e.unit_price = 'Must be > 0'
    if (Number(form.stock) < 0) e.stock = 'Cannot be negative'
    if (Number(form.reorder_threshold) < 0) e.reorder_threshold = 'Cannot be negative'
    if (form.expiry_date) {
      const today = new Date().toISOString().slice(0, 10)
      if (form.expiry_date < today && !isEdit) e.expiry_date = 'Must be a future date'
    }
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const submit = async (ev) => {
    ev.preventDefault()
    if (!validate()) return
    setSaving(true)
    try {
      const payload = {
        ...(isEdit ? {} : { sku: form.sku }),
        name: form.name,
        category: form.category,
        unit_price: Number(form.unit_price),
        stock: Number(form.stock),
        reorder_threshold: Number(form.reorder_threshold),
        expiry_date: form.expiry_date || null,
        preferred_supplier_id: form.preferred_supplier_id ? Number(form.preferred_supplier_id) : null,
      }
      if (isEdit) await productsApi.update(product.id, payload)
      else await productsApi.create(payload)
      toast.success(isEdit ? 'Product updated' : 'Product created')
      onSaved()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50">
      <form onSubmit={submit} className="card w-full max-w-lg space-y-3">
        <h2 className="text-lg font-semibold">{isEdit ? 'Edit Product' : 'New Product'}</h2>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">SKU</label>
            <input className="input" value={form.sku} onChange={change('sku')} disabled={isEdit} />
            {errors.sku && <p className="text-xs text-red-600">{errors.sku}</p>}
          </div>
          <div>
            <label className="label">Category</label>
            <input className="input" value={form.category} onChange={change('category')} />
            {errors.category && <p className="text-xs text-red-600">{errors.category}</p>}
          </div>
        </div>
        <div>
          <label className="label">Name</label>
          <input className="input" value={form.name} onChange={change('name')} />
          {errors.name && <p className="text-xs text-red-600">{errors.name}</p>}
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="label">Unit price (₹)</label>
            <input type="number" step="0.01" className="input" value={form.unit_price} onChange={change('unit_price')} />
            {errors.unit_price && <p className="text-xs text-red-600">{errors.unit_price}</p>}
          </div>
          <div>
            <label className="label">Stock</label>
            <input type="number" className="input" value={form.stock} onChange={change('stock')} />
            {errors.stock && <p className="text-xs text-red-600">{errors.stock}</p>}
          </div>
          <div>
            <label className="label">Reorder ≤</label>
            <input type="number" className="input" value={form.reorder_threshold} onChange={change('reorder_threshold')} />
            {errors.reorder_threshold && <p className="text-xs text-red-600">{errors.reorder_threshold}</p>}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Expiry date</label>
            <input type="date" className="input" value={form.expiry_date || ''} onChange={change('expiry_date')} />
            {errors.expiry_date && <p className="text-xs text-red-600">{errors.expiry_date}</p>}
          </div>
          <div>
            <label className="label">Preferred supplier</label>
            <select className="input" value={form.preferred_supplier_id || ''} onChange={change('preferred_supplier_id')}>
              <option value="">— none —</option>
              {suppliers.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
          <button disabled={saving} className="btn-primary">{saving ? '…' : 'Save'}</button>
        </div>
      </form>
    </div>
  )
}

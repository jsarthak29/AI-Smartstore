import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { invoicesApi, productsApi, suppliersApi } from '../api/resources.js'

export default function InvoiceUploadPage() {
  const qc = useQueryClient()
  const [file, setFile] = useState(null)
  const [parsed, setParsed] = useState(null)
  const [invoiceId, setInvoiceId] = useState(null)
  const [supplierId, setSupplierId] = useState('')

  const { data: products } = useQuery({
    queryKey: ['products-flat'],
    queryFn: () => productsApi.list({ page: 1, page_size: 200 }).then(d => d.items),
  })
  const { data: suppliers } = useQuery({ queryKey: ['suppliers'], queryFn: suppliersApi.list })

  const parse = useMutation({
    mutationFn: invoicesApi.parse,
    onSuccess: (data) => {
      setParsed(data.parsed)
      setInvoiceId(data.invoice_id)
      toast.success('Invoice parsed — review and confirm')
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Parse failed'),
  })

  const receive = useMutation({
    mutationFn: invoicesApi.receive,
    onSuccess: () => {
      toast.success('Stock received')
      setFile(null); setParsed(null); setInvoiceId(null); setSupplierId('')
      qc.invalidateQueries({ queryKey: ['products'] })
      qc.invalidateQueries({ queryKey: ['dashboard-summary'] })
    },
    onError: (e) => toast.error(e.response?.data?.detail || 'Failed'),
  })

  const upload = (ev) => {
    ev.preventDefault()
    if (!file) return toast.error('Choose a file')
    parse.mutate(file)
  }

  const updateLine = (i, k, v) => {
    setParsed({
      ...parsed,
      line_items: parsed.line_items.map((li, idx) => idx === i ? { ...li, [k]: v } : li),
    })
  }

  const confirm = () => {
    const lines = (parsed?.line_items || [])
      .filter((li) => li.matched_product_id && Number(li.qty) > 0)
      .map((li) => ({
        product_id: Number(li.matched_product_id),
        qty: Math.round(Number(li.qty)),
        unit_price: Number(li.unit_price) || 0,
      }))
    if (lines.length === 0) return toast.error('Match at least one line item to a product')
    receive.mutate({
      invoice_id: invoiceId,
      supplier_id: supplierId ? Number(supplierId) : null,
      lines,
    })
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Invoice Upload</h1>

      <form onSubmit={upload} className="card flex flex-col sm:flex-row gap-3 items-start sm:items-end">
        <div className="flex-1">
          <label className="label">Invoice (JPG / PNG / PDF)</label>
          <input type="file" accept=".jpg,.jpeg,.png,.pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        </div>
        <button disabled={parse.isPending} className="btn-primary">{parse.isPending ? 'Parsing…' : 'Parse invoice'}</button>
      </form>

      {parsed && (
        <div className="card space-y-4">
          <h2 className="font-semibold">Review parsed data</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="label">Supplier (detected: {parsed.supplier_name || '—'})</label>
              <select className="input" value={supplierId} onChange={(e) => setSupplierId(e.target.value)}>
                <option value="">— pick supplier —</option>
                {(suppliers || []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Invoice date</label>
              <input className="input" value={parsed.invoice_date || ''} readOnly />
            </div>
            <div>
              <label className="label">Grand total</label>
              <input className="input" value={parsed.grand_total ?? ''} readOnly />
            </div>
          </div>

          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="py-2 px-2">Line</th>
                <th className="py-2 px-2">Qty</th>
                <th className="py-2 px-2">Unit Price</th>
                <th className="py-2 px-2">Match to product</th>
              </tr>
            </thead>
            <tbody>
              {parsed.line_items.map((li, i) => (
                <tr key={i} className="border-b border-slate-100">
                  <td className="py-2 px-2">{li.name}</td>
                  <td className="py-2 px-2">
                    <input type="number" className="input w-20" value={li.qty || 0} onChange={(e) => updateLine(i, 'qty', e.target.value)} />
                  </td>
                  <td className="py-2 px-2">
                    <input type="number" step="0.01" className="input w-24" value={li.unit_price || 0} onChange={(e) => updateLine(i, 'unit_price', e.target.value)} />
                  </td>
                  <td className="py-2 px-2">
                    <select className="input" value={li.matched_product_id || ''} onChange={(e) => updateLine(i, 'matched_product_id', e.target.value)}>
                      <option value="">— match —</option>
                      {(products || []).map((p) => <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>)}
                    </select>
                  </td>
                </tr>
              ))}
              {parsed.line_items.length === 0 && (
                <tr><td colSpan={4} className="py-4 text-center text-slate-400 text-sm">No line items detected. Add manually or re-upload a clearer image.</td></tr>
              )}
            </tbody>
          </table>

          <div className="text-right">
            <button disabled={receive.isPending} className="btn-primary" onClick={confirm}>
              {receive.isPending ? 'Saving…' : 'Confirm goods received'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

const LABEL = { ok: 'OK', low: 'Low', critical: 'Critical', expired: 'Expired' }

export default function StockBadge({ status }) {
  const cls = `badge badge-${status || 'ok'}`
  return <span className={cls}>{LABEL[status] || status}</span>
}

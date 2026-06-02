export default function EmptyState({ title = 'Nothing here yet', hint }) {
  return (
    <div className="text-center py-12 text-slate-500">
      <div className="text-base font-medium">{title}</div>
      {hint && <div className="text-sm mt-1">{hint}</div>}
    </div>
  )
}

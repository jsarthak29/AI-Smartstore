export function SkeletonRow({ cols = 5 }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="py-3 px-3">
          <div className="h-3 bg-slate-200 rounded animate-pulse" />
        </td>
      ))}
    </tr>
  )
}

export function SkeletonCard() {
  return <div className="card animate-pulse h-24" />
}

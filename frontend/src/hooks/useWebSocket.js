import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

export function useWebSocket() {
  const qc = useQueryClient()

  useEffect(() => {
    let ws
    try {
      ws = new WebSocket(`${WS_URL}/ws`)
    } catch {
      return
    }
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        if (msg.type === 'stock_update') {
          qc.invalidateQueries({ queryKey: ['products'] })
          qc.invalidateQueries({ queryKey: ['dashboard-summary'] })
          toast(`Stock updated for #${msg.product_id} → ${msg.new_stock}`, { icon: '📦' })
        }
      } catch { /* ignore */ }
    }
    return () => { try { ws?.close() } catch {} }
  }, [qc])
}

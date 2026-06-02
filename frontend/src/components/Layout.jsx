import { NavLink, Outlet } from 'react-router-dom'
import ChatPanel from './ChatPanel.jsx'
import { useWebSocket } from '../hooks/useWebSocket.js'

const nav = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/products', label: 'Products' },
  { to: '/suppliers', label: 'Suppliers' },
  { to: '/purchase-orders', label: 'Purchase Orders' },
  { to: '/invoices', label: 'Invoice Upload' },
  { to: '/automation', label: 'Automation Logs' },
  { to: '/reports', label: 'Reports' },
  { to: '/chat', label: 'AI Assistant' },
]

export default function Layout() {
  useWebSocket()

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 bg-slate-900 text-slate-100 flex flex-col">
        <div className="px-4 py-5 text-lg font-semibold border-b border-slate-800">SmartStore AI</div>
        <nav className="flex-1 px-2 py-4 space-y-1">
          {nav.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) =>
                `block px-3 py-2 rounded text-sm ${isActive ? 'bg-brand-600 text-white' : 'hover:bg-slate-800'}`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-3 py-3 border-t border-slate-800 text-xs text-slate-400">
          SmartStore AI
        </div>
      </aside>
      <main className="flex-1 p-6 overflow-auto">
        <Outlet />
      </main>
      <ChatPanel />
    </div>
  )
}

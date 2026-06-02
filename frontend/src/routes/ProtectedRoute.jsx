import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/authStore.js'

export default function ProtectedRoute({ children, role }) {
  const location = useLocation()
  const accessToken = useAuthStore((s) => s.accessToken)
  const user = useAuthStore((s) => s.user)

  if (!accessToken) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  if (role && user && user.role !== role) {
    return <Navigate to="/dashboard" replace />
  }
  return children
}

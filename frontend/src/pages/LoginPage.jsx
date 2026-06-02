import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { login, me, registerTenant } from '../api/auth.js'
import { useAuthStore } from '../store/authStore.js'

export default function LoginPage() {
  const navigate = useNavigate()
  const { setTokens, setUser } = useAuthStore()
  const [email, setEmail] = useState('admin@smartstore.app')
  const [password, setPassword] = useState('admin123')
  const [mode, setMode] = useState('login') // login | register
  const [tenant, setTenant] = useState('My Store')
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState({})

  const validate = () => {
    const e = {}
    if (!email.includes('@')) e.email = 'enter a valid email'
    if (password.length < 6) e.password = 'minimum 6 characters'
    if (mode === 'register' && tenant.trim().length < 2) e.tenant = 'tenant name required'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const submit = async (ev) => {
    ev.preventDefault()
    if (!validate()) return
    setLoading(true)
    try {
      if (mode === 'register') {
        await registerTenant(tenant, email, password)
        toast.success('Tenant created — logging you in')
      }
      const tokens = await login(email, password)
      setTokens(tokens)
      const u = await me()
      setUser(u)
      toast.success(`Welcome ${u.email}`)
      navigate('/dashboard')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 px-4">
      <form onSubmit={submit} className="card w-full max-w-md space-y-4">
        <h1 className="text-xl font-semibold">SmartStore AI — {mode === 'login' ? 'Sign In' : 'Register Tenant'}</h1>
        {mode === 'register' && (
          <div>
            <label className="label">Store / tenant name</label>
            <input className="input" value={tenant} onChange={(e) => setTenant(e.target.value)} />
            {errors.tenant && <p className="text-xs text-red-600 mt-1">{errors.tenant}</p>}
          </div>
        )}
        <div>
          <label className="label">Email</label>
          <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} />
          {errors.email && <p className="text-xs text-red-600 mt-1">{errors.email}</p>}
        </div>
        <div>
          <label className="label">Password</label>
          <input type="password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} />
          {errors.password && <p className="text-xs text-red-600 mt-1">{errors.password}</p>}
        </div>
        <button disabled={loading} className="btn-primary w-full" type="submit">
          {loading ? '…' : (mode === 'login' ? 'Sign in' : 'Create account')}
        </button>
        <p className="text-xs text-slate-500 text-center">
          {mode === 'login' ? (
            <>No account? <button type="button" className="text-brand-600" onClick={() => setMode('register')}>Register a tenant</button></>
          ) : (
            <>Have an account? <button type="button" className="text-brand-600" onClick={() => setMode('login')}>Sign in</button></>
          )}
        </p>
        <p className="text-xs text-slate-400 text-center">
          Seeded demo: admin@smartstore.app / admin123
        </p>
      </form>
    </div>
  )
}

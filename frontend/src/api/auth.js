import { apiClient } from './client.js'

export async function login(email, password) {
  const body = new URLSearchParams()
  body.append('username', email)
  body.append('password', password)
  const res = await apiClient.post('/auth/login', body, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return res.data
}

export async function me() {
  const res = await apiClient.get('/auth/me')
  return res.data
}

export async function registerTenant(tenantName, email, password) {
  const res = await apiClient.post('/auth/register-tenant', {
    tenant_name: tenantName,
    admin_email: email,
    admin_password: password,
  })
  return res.data
}

import { apiClient } from './client.js'

export const productsApi = {
  list: (params) => apiClient.get('/products', { params }).then(r => r.data),
  get: (id) => apiClient.get(`/products/${id}`).then(r => r.data),
  create: (body) => apiClient.post('/products', body).then(r => r.data),
  update: (id, body) => apiClient.patch(`/products/${id}`, body).then(r => r.data),
  remove: (id) => apiClient.delete(`/products/${id}`).then(r => r.data),
  forecast: (id) => apiClient.get(`/products/${id}/forecast`).then(r => r.data),
}

export const suppliersApi = {
  list: () => apiClient.get('/suppliers').then(r => r.data),
  create: (body) => apiClient.post('/suppliers', body).then(r => r.data),
  update: (id, body) => apiClient.patch(`/suppliers/${id}`, body).then(r => r.data),
  remove: (id) => apiClient.delete(`/suppliers/${id}`).then(r => r.data),
}

export const posApi = {
  list: (params) => apiClient.get('/purchase-orders', { params }).then(r => r.data),
  create: (body) => apiClient.post('/purchase-orders', body).then(r => r.data),
  updateStatus: (id, status) =>
    apiClient.patch(`/purchase-orders/${id}/status`, { status }).then(r => r.data),
  sendEmail: (id) => apiClient.post(`/purchase-orders/${id}/send-email`).then(r => r.data),
}

export const aiApi = {
  chat: (messages) => apiClient.post('/ai/chat', { messages }).then(r => r.data),
}

export const invoicesApi = {
  parse: (file) => {
    const form = new FormData()
    form.append('file', file)
    return apiClient.post('/invoices/parse', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },
  receive: (body) => apiClient.post('/inventory/receive', body).then(r => r.data),
}

export const automationApi = {
  logs: () => apiClient.get('/automation/logs').then(r => r.data),
  reports: () => apiClient.get('/reports').then(r => r.data),
  runNow: (jobName) => apiClient.post(`/automation/run/${jobName}`).then(r => r.data),
  summary: () => apiClient.get('/dashboard/summary').then(r => r.data),
}

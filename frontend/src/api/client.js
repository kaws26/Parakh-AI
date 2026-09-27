import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 120000,
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('viva_access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  if (!(config.data instanceof FormData)) config.headers['Content-Type'] = 'application/json'
  return config
})

apiClient.interceptors.response.use((response) => response, (error) => {
  if (error.response?.status === 401) window.dispatchEvent(new Event('viva:unauthorized'))
  const detail = error.response?.data?.detail
  error.userMessage = typeof detail === 'string' ? detail : 'The service could not complete this request. Please try again.'
  return Promise.reject(error)
})

export const checkHealth = async () => {
  const response = await apiClient.get('/api/health')
  return response.data
}

export default apiClient

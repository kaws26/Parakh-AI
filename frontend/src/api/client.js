import axios from 'axios'

const apiClient = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
})

export const checkHealth = async () => {
  const response = await apiClient.get('/api/health')
  return response.data
}

export default apiClient

import { useState, useEffect } from 'react'
import { checkHealth } from './api/client'
import './App.css'

function App() {
  const [healthData, setHealthData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchHealth = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await checkHealth()
      setHealthData(data)
    } catch (err) {
      setError(err.message || 'Failed to connect to backend service')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHealth()
  }, [])

  return (
    <main className="app-container">
      <header className="app-header">
        <div className="badge">AI-Based Viva Voce System</div>
        <h1>Hello, Viva!</h1>
        <p className="subtitle">
          Automated oral examination platform with speech evaluation and RAG-powered assessment.
        </p>
      </header>

      <section className="status-card">
        <h2>System Status (Phase 0 Foundation)</h2>

        {loading && (
          <div className="status-loading">
            <span className="spinner"></span> Checking backend &amp; database health...
          </div>
        )}

        {error && (
          <div className="status-error">
            <p><strong>Connection Error:</strong> {error}</p>
            <p className="hint">Ensure FastAPI backend is running on port 8000.</p>
            <button className="btn" onClick={fetchHealth}>Retry Connection</button>
          </div>
        )}

        {healthData && !loading && (
          <div className="status-details">
            <div className="status-row">
              <span className="label">Backend Status:</span>
              <span className="value badge-success">{healthData.status}</span>
            </div>
            <div className="status-row">
              <span className="label">Database Status:</span>
              <span className="value badge-success">{healthData.db}</span>
            </div>
            <div className="status-row">
              <span className="label">Message:</span>
              <span className="value message-text">{healthData.message}</span>
            </div>

            <button className="btn btn-refresh" onClick={fetchHealth}>
              Refresh Health Check
            </button>
          </div>
        )}
      </section>

      <footer className="app-footer">
        <p>Phase 0: Setup &amp; Foundations Complete</p>
      </footer>
    </main>
  )
}

export default App

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '../api'
import { Shield, Loader2 } from 'lucide-react'

export default function LoginPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await authApi.login(username, password)
      localStorage.setItem('admin_token', res.data.access_token)
      navigate('/admin')
    } catch {
      setError('Неверный логин или пароль')
    }
    setLoading(false)
  }

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-primary/10 rounded-xl flex items-center justify-center mx-auto mb-4">
            <Shield className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-2xl font-bold text-text">Вход для администраторов</h1>
          <p className="text-text-muted text-sm mt-2">Панель управления турниром</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-surface rounded-xl border border-border shadow-sm p-6 space-y-4">
          {error && (
            <div className="bg-danger/5 border border-danger/20 text-danger rounded-lg px-4 py-3 text-sm">{error}</div>
          )}
          <div>
            <label className="block text-sm text-text-secondary mb-1.5 font-medium">Логин</label>
            <input
              type="text" value={username} onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 bg-surface-light border border-border rounded-lg text-text focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20"
              placeholder="admin"
            />
          </div>
          <div>
            <label className="block text-sm text-text-secondary mb-1.5 font-medium">Пароль</label>
            <input
              type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 bg-surface-light border border-border rounded-lg text-text focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20"
              placeholder="********"
            />
          </div>
          <button
            type="submit" disabled={loading}
            className="w-full py-3 bg-primary hover:bg-primary-dark text-white rounded-lg font-medium cursor-pointer border-none transition-colors disabled:opacity-50"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Вход...</span>
            ) : 'Войти'}
          </button>
        </form>
      </div>
    </div>
  )
}

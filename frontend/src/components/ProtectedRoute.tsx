import { useEffect, useState } from 'react'
import { Navigate, Outlet } from 'react-router-dom'
import { authApi } from '../api'
import { Loader2 } from 'lucide-react'

export default function ProtectedRoute() {
  const [status, setStatus] = useState<'loading' | 'ok' | 'denied'>('loading')

  useEffect(() => {
    const token = localStorage.getItem('admin_token')
    if (!token) {
      setStatus('denied')
      return
    }
    authApi.getMe().then(() => setStatus('ok')).catch(() => {
      localStorage.removeItem('admin_token')
      setStatus('denied')
    })
  }, [])

  if (status === 'loading') {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-text-muted" />
      </div>
    )
  }

  if (status === 'denied') {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}

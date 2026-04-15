import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { Menu, X, Shield, LogOut, Sun, Moon } from 'lucide-react'

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [isAdmin, setIsAdmin] = useState(false)
  const [dark, setDark] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('theme') === 'dark'
    }
    return false
  })

  useEffect(() => {
    if (dark) {
      document.documentElement.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }, [dark])

  useEffect(() => {
    setIsAdmin(!!localStorage.getItem('admin_token'))
  }, [location])

  const logout = () => {
    localStorage.removeItem('admin_token')
    setIsAdmin(false)
    navigate('/')
  }

  const navLinks = [
    { to: '/', label: 'Главная' },
    { to: '/participants', label: 'Участники' },
    { to: '/brackets', label: 'Сетки' },
    { to: '/register', label: 'Регистрация' },
  ]

  const adminLinks = [
    { to: '/admin', label: 'Панель' },
    { to: '/admin/participants', label: 'Участники' },
    { to: '/admin/brackets', label: 'Сетки' },
  ]

  const isActive = (path: string) => location.pathname === path

  return (
    <div className="min-h-screen flex flex-col bg-surface-light">
      <header className="bg-nav shadow-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 no-underline">
            <div className="w-9 h-9 bg-accent rounded flex items-center justify-center text-white font-bold text-sm tracking-wide">
              ТБ
            </div>
            <div className="hidden sm:block">
              <span className="text-sm font-semibold text-white/95 tracking-wide uppercase">Тайский бокс</span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-0.5">
            {navLinks.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className={`px-3.5 py-2 rounded text-sm font-medium transition-colors no-underline ${
                  isActive(link.to)
                    ? 'bg-white/20 text-white'
                    : 'text-white/70 hover:text-white hover:bg-white/10'
                }`}
              >
                {link.label}
              </Link>
            ))}

            {isAdmin && (
              <>
                <div className="w-px h-5 bg-white/20 mx-2" />
                {adminLinks.map((link) => (
                  <Link
                    key={link.to}
                    to={link.to}
                    className={`px-3.5 py-2 rounded text-sm font-medium transition-colors no-underline ${
                      isActive(link.to)
                        ? 'bg-accent/30 text-accent'
                        : 'text-white/70 hover:text-white hover:bg-white/10'
                    }`}
                  >
                    <span className="flex items-center gap-1.5">
                      <Shield className="w-3 h-3" />
                      {link.label}
                    </span>
                  </Link>
                ))}
                <button
                  onClick={logout}
                  className="px-3 py-2 rounded text-sm font-medium text-white/50 hover:text-danger transition-colors cursor-pointer bg-transparent border-none"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </>
            )}

            {!isAdmin && (
              <Link
                to="/login"
                className="px-3 py-2 rounded text-sm font-medium text-white/40 hover:text-white/70 transition-colors no-underline"
              >
                <Shield className="w-4 h-4" />
              </Link>
            )}

            <div className="w-px h-5 bg-white/20 mx-2" />
            <button
              onClick={() => setDark(!dark)}
              className="p-2 rounded text-white/60 hover:text-white hover:bg-white/10 transition-colors cursor-pointer bg-transparent border-none"
              title={dark ? 'Светлая тема' : 'Тёмная тема'}
            >
              {dark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
          </nav>

          <div className="flex items-center gap-2 md:hidden">
            <button
              onClick={() => setDark(!dark)}
              className="p-2 text-white/60 hover:text-white transition-colors cursor-pointer bg-transparent border-none"
            >
              {dark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
            <button
              className="p-2 text-white/70 bg-transparent border-none cursor-pointer"
              onClick={() => setMenuOpen(!menuOpen)}
            >
              {menuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {menuOpen && (
          <div className="md:hidden border-t border-white/10 bg-nav-dark px-4 py-3 space-y-1">
            {navLinks.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                onClick={() => setMenuOpen(false)}
                className={`block px-3 py-2 rounded text-sm font-medium no-underline ${
                  isActive(link.to) ? 'bg-white/15 text-white' : 'text-white/70'
                }`}
              >
                {link.label}
              </Link>
            ))}
            {isAdmin && adminLinks.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                onClick={() => setMenuOpen(false)}
                className={`block px-3 py-2 rounded text-sm font-medium no-underline ${
                  isActive(link.to) ? 'bg-accent/20 text-accent' : 'text-white/70'
                }`}
              >
                {link.label}
              </Link>
            ))}
            {!isAdmin && (
              <Link to="/login" onClick={() => setMenuOpen(false)} className="block px-3 py-2 rounded text-sm font-medium text-white/50 no-underline">
                Вход для администраторов
              </Link>
            )}
          </div>
        )}
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="bg-nav text-white/60 py-8 text-center text-sm">
        <p className="font-medium">Чемпионат и Первенство Республики Башкортостан по муайтай</p>
        <p className="mt-1 text-white/40 text-xs">&copy; 2026 Федерация Муайтай РБ. Все права защищены.</p>
      </footer>
    </div>
  )
}

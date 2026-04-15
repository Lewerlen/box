import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { Menu, X, Shield, LogOut } from 'lucide-react'

export default function Layout() {
  const location = useLocation()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [isAdmin, setIsAdmin] = useState(false)

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
    <div className="min-h-screen flex flex-col">
      <header className="bg-surface-light border-b border-border sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 no-underline">
            <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center text-white font-bold text-lg">
              MT
            </div>
            <span className="text-lg font-semibold text-text hidden sm:block">Muay Thai</span>
          </Link>

          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors no-underline ${
                  isActive(link.to)
                    ? 'bg-primary/10 text-primary'
                    : 'text-text-secondary hover:text-text hover:bg-surface-lighter/50'
                }`}
              >
                {link.label}
              </Link>
            ))}

            {isAdmin && (
              <>
                <div className="w-px h-6 bg-border mx-2" />
                {adminLinks.map((link) => (
                  <Link
                    key={link.to}
                    to={link.to}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors no-underline ${
                      isActive(link.to)
                        ? 'bg-accent/10 text-accent'
                        : 'text-text-secondary hover:text-text hover:bg-surface-lighter/50'
                    }`}
                  >
                    <span className="flex items-center gap-1">
                      <Shield className="w-3 h-3" />
                      {link.label}
                    </span>
                  </Link>
                ))}
                <button
                  onClick={logout}
                  className="px-3 py-2 rounded-lg text-sm font-medium text-text-muted hover:text-danger transition-colors cursor-pointer bg-transparent border-none"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </>
            )}

            {!isAdmin && (
              <Link
                to="/login"
                className="px-3 py-2 rounded-lg text-sm font-medium text-text-muted hover:text-text transition-colors no-underline"
              >
                <Shield className="w-4 h-4" />
              </Link>
            )}
          </nav>

          <button
            className="md:hidden p-2 text-text-secondary bg-transparent border-none cursor-pointer"
            onClick={() => setMenuOpen(!menuOpen)}
          >
            {menuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {menuOpen && (
          <div className="md:hidden border-t border-border bg-surface-light px-4 py-3 space-y-1">
            {navLinks.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                onClick={() => setMenuOpen(false)}
                className={`block px-3 py-2 rounded-lg text-sm font-medium no-underline ${
                  isActive(link.to) ? 'bg-primary/10 text-primary' : 'text-text-secondary'
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
                className={`block px-3 py-2 rounded-lg text-sm font-medium no-underline ${
                  isActive(link.to) ? 'bg-accent/10 text-accent' : 'text-text-secondary'
                }`}
              >
                {link.label}
              </Link>
            ))}
            {!isAdmin && (
              <Link to="/login" onClick={() => setMenuOpen(false)} className="block px-3 py-2 rounded-lg text-sm font-medium text-text-muted no-underline">
                Вход для администраторов
              </Link>
            )}
          </div>
        )}
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="bg-surface-light border-t border-border py-6 text-center text-text-muted text-sm">
        <p>Чемпионат и Первенство Республики Башкортостан по муайтай</p>
      </footer>
    </div>
  )
}

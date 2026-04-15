import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { publicApi } from '../api'
import { Users, MapPin, Trophy, UserPlus } from 'lucide-react'

interface Stats {
  total_participants: number
  total_clubs: number
  total_regions: number
  male_count: number
  female_count: number
}

export default function HomePage() {
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    publicApi.getStats().then((r) => setStats(r.data)).catch(() => {})
  }, [])

  return (
    <div>
      <section className="relative bg-nav overflow-hidden">
        <svg className="absolute left-4 md:left-12 bottom-0 w-40 h-64 md:w-56 md:h-80 opacity-10" viewBox="0 0 200 320" fill="white" xmlns="http://www.w3.org/2000/svg">
          <path d="M100 10 C95 10, 90 15, 90 22 C90 29, 95 34, 100 34 C105 34, 110 29, 110 22 C110 15, 105 10, 100 10 Z M85 40 L75 90 L55 75 L45 85 L75 110 L70 160 L50 260 L40 310 L60 310 L80 220 L85 180 L90 220 L110 310 L130 310 L120 260 L100 160 L95 110 L140 130 L155 100 L140 90 L95 75 L115 40 Z" />
        </svg>
        <svg className="absolute right-4 md:right-12 bottom-0 w-40 h-64 md:w-56 md:h-80 opacity-10" viewBox="0 0 200 320" fill="white" xmlns="http://www.w3.org/2000/svg">
          <path d="M100 10 C95 10, 90 15, 90 22 C90 29, 95 34, 100 34 C105 34, 110 29, 110 22 C110 15, 105 10, 100 10 Z M90 38 L80 55 L40 50 L35 65 L78 78 L72 100 L60 105 L30 160 L20 310 L45 310 L60 180 L75 140 L78 160 L70 310 L95 310 L105 180 L108 140 L115 160 L130 310 L155 310 L135 160 L120 105 L108 100 L102 78 L145 65 L140 50 L100 55 L110 38 Z" />
        </svg>
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-nav-dark/50" />
        <div className="relative max-w-7xl mx-auto px-4 py-20 md:py-28 text-center">
          <h1 className="text-3xl md:text-5xl lg:text-6xl font-bold mb-6 text-white leading-tight">
            Чемпионат и Первенство
            <br />
            Республики Башкортостан
            <br />
            <span className="text-accent">по муайтай</span>
          </h1>
          <p className="text-white/60 text-base md:text-lg mb-10 max-w-2xl mx-auto">
            Управление турниром, регистрация участников, просмотр турнирных сеток и результатов
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link
              to="/register"
              className="px-8 py-3.5 bg-accent hover:bg-accent-dark text-white rounded-lg font-semibold transition-all shadow-lg no-underline"
            >
              <span className="flex items-center gap-2">
                <UserPlus className="w-5 h-5" />
                Регистрация участника
              </span>
            </Link>
            <Link
              to="/participants"
              className="px-8 py-3.5 bg-white/10 hover:bg-white/20 text-white border border-white/20 rounded-lg font-semibold transition-all no-underline"
            >
              Список участников
            </Link>
          </div>
        </div>
      </section>

      {stats && (
        <section className="max-w-7xl mx-auto px-4 -mt-10 relative z-10">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { icon: Users, label: 'Участников', value: stats.total_participants, color: 'text-primary' },
              { icon: Trophy, label: 'Клубов', value: stats.total_clubs, color: 'text-accent' },
              { icon: MapPin, label: 'Регионов', value: stats.total_regions, color: 'text-success' },
              { icon: Users, label: 'Муж / Жен', value: `${stats.male_count} / ${stats.female_count}`, color: 'text-primary-light' },
            ].map((stat, i) => (
              <div key={i} className="bg-surface rounded-xl p-6 border border-border-light shadow-sm text-center">
                <stat.icon className={`w-7 h-7 mx-auto mb-3 ${stat.color}`} />
                <div className="text-3xl font-bold mb-1 text-text">{stat.value}</div>
                <div className="text-text-muted text-sm">{stat.label}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="max-w-7xl mx-auto px-4 py-16">
        <h2 className="text-2xl font-bold text-text mb-8 text-center">Разделы турнира</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {[
            { to: '/participants', title: 'Участники', desc: 'Список всех зарегистрированных участников с фильтрами по полу, возрасту, весу, классу и клубу', icon: Users },
            { to: '/brackets', title: 'Турнирные сетки', desc: 'Просмотр утверждённых турнирных сеток по категориям', icon: Trophy },
            { to: '/register', title: 'Регистрация', desc: 'Зарегистрировать нового участника на турнир', icon: UserPlus },
          ].map((card) => (
            <Link
              key={card.to}
              to={card.to}
              className="group bg-surface rounded-xl p-8 border border-border-light hover:border-primary/30 hover:shadow-md transition-all no-underline"
            >
              <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4 group-hover:bg-primary/15 transition-colors">
                <card.icon className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-lg font-semibold mb-2 text-text">{card.title}</h3>
              <p className="text-text-muted text-sm leading-relaxed">{card.desc}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}

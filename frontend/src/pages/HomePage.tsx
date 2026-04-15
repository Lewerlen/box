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
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/20 via-surface to-surface" />
        <div className="relative max-w-7xl mx-auto px-4 py-20 md:py-32 text-center">
          <h1 className="text-4xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-white via-white to-text-secondary bg-clip-text text-transparent">
            Чемпионат и Первенство
            <br />
            <span className="text-primary">Республики Башкортостан</span>
            <br />
            по муайтай
          </h1>
          <p className="text-text-secondary text-lg md:text-xl mb-10 max-w-2xl mx-auto">
            Управление турниром, регистрация участников, просмотр турнирных сеток и результатов
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link
              to="/register"
              className="px-8 py-3 bg-primary hover:bg-primary-dark text-white rounded-xl font-semibold transition-all shadow-lg shadow-primary/25 no-underline"
            >
              <span className="flex items-center gap-2">
                <UserPlus className="w-5 h-5" />
                Регистрация участника
              </span>
            </Link>
            <Link
              to="/participants"
              className="px-8 py-3 bg-surface-light hover:bg-surface-lighter text-text border border-border rounded-xl font-semibold transition-all no-underline"
            >
              Список участников
            </Link>
          </div>
        </div>
      </section>

      {stats && (
        <section className="max-w-7xl mx-auto px-4 py-16">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { icon: Users, label: 'Участников', value: stats.total_participants, color: 'text-primary' },
              { icon: Trophy, label: 'Клубов', value: stats.total_clubs, color: 'text-accent' },
              { icon: MapPin, label: 'Регионов', value: stats.total_regions, color: 'text-success' },
              { icon: Users, label: 'Муж / Жен', value: `${stats.male_count} / ${stats.female_count}`, color: 'text-blue-400' },
            ].map((stat, i) => (
              <div key={i} className="bg-surface-light rounded-2xl p-6 border border-border text-center">
                <stat.icon className={`w-8 h-8 mx-auto mb-3 ${stat.color}`} />
                <div className="text-3xl font-bold mb-1">{stat.value}</div>
                <div className="text-text-muted text-sm">{stat.label}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="max-w-7xl mx-auto px-4 py-16">
        <div className="grid md:grid-cols-3 gap-6">
          {[
            { to: '/participants', title: 'Участники', desc: 'Список всех зарегистрированных участников с фильтрами по полу, возрасту, весу, классу и клубу', icon: Users },
            { to: '/brackets', title: 'Турнирные сетки', desc: 'Просмотр утвержденных турнирных сеток по категориям', icon: Trophy },
            { to: '/register', title: 'Регистрация', desc: 'Зарегистрировать нового участника на турнир', icon: UserPlus },
          ].map((card) => (
            <Link
              key={card.to}
              to={card.to}
              className="group bg-surface-light rounded-2xl p-8 border border-border hover:border-primary/50 transition-all no-underline"
            >
              <card.icon className="w-10 h-10 text-primary mb-4 group-hover:scale-110 transition-transform" />
              <h3 className="text-xl font-semibold mb-2 text-text">{card.title}</h3>
              <p className="text-text-muted text-sm">{card.desc}</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}

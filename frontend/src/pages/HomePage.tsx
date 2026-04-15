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
      <section className="relative bg-primary overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 right-0 w-96 h-96 bg-accent rounded-full -translate-y-1/2 translate-x-1/3" />
          <div className="absolute bottom-0 left-0 w-64 h-64 bg-white rounded-full translate-y-1/3 -translate-x-1/4" />
        </div>
        <div className="relative max-w-7xl mx-auto px-4 py-20 md:py-28 text-center">
          <div className="inline-block mb-6 px-4 py-1.5 bg-accent/20 border border-accent/30 rounded-full">
            <span className="text-accent text-sm font-semibold tracking-wide uppercase">Официальный турнир</span>
          </div>
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

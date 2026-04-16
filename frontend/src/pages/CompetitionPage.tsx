import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { competitionsApi } from '../api'
import { Calendar, MapPin, Users, Trophy, UserPlus, ChevronLeft, Clock } from 'lucide-react'

interface Competition {
  id: number
  name: string
  discipline: 'muay_thai' | 'kickboxing'
  date_start: string | null
  date_end: string | null
  location: string | null
  status: 'active' | 'upcoming' | 'finished'
  participants_count: number
  registration_deadline: string | null
  registration_open_at: string | null
  registration_closed: boolean
}

const DISCIPLINE_LABEL: Record<string, string> = {
  muay_thai: 'Тайский бокс',
  kickboxing: 'Кикбоксинг',
}

const DISCIPLINE_COLORS: Record<string, string> = {
  muay_thai: 'bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30',
  kickboxing: 'bg-blue-500/15 text-blue-600 dark:text-blue-400 border border-blue-500/30',
}

const STATUS_LABEL: Record<string, string> = {
  active: 'Идёт регистрация',
  upcoming: 'Скоро',
  finished: 'Завершено',
}

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-500/15 text-green-700 dark:text-green-400 border border-green-500/30',
  upcoming: 'bg-yellow-500/15 text-yellow-700 dark:text-yellow-400 border border-yellow-500/30',
  finished: 'bg-gray-500/15 text-gray-600 dark:text-gray-400 border border-gray-500/30',
}

function formatDateRange(start: string | null, end: string | null): string {
  if (!start) return '—'
  const fmt = (d: string) =>
    new Date(d).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
  if (!end || start === end) return fmt(start)
  const s = new Date(start)
  const e = new Date(end)
  if (s.getFullYear() === e.getFullYear() && s.getMonth() === e.getMonth()) {
    return `${s.getDate()}–${e.getDate()} ${e.toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' })}`
  }
  return `${fmt(start)} – ${fmt(end)}`
}

export default function CompetitionPage() {
  const { id } = useParams<{ id: string }>()
  const [comp, setComp] = useState<Competition | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    if (!id) return
    competitionsApi.getById(Number(id))
      .then((r) => setComp(r.data))
      .catch((e) => {
        if (e.response?.status === 404) setNotFound(true)
      })
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return <div className="text-center py-20 text-text-muted">Загрузка...</div>
  }

  if (notFound || !comp) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-20 text-center">
        <p className="text-text-muted text-lg mb-6">Соревнование не найдено</p>
        <Link to="/" className="text-primary hover:underline">← На главную</Link>
      </div>
    )
  }

  const isActive = comp.status === 'active'

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-text-muted hover:text-text mb-6 no-underline">
        <ChevronLeft className="w-4 h-4" />
        Все соревнования
      </Link>

      <div className="bg-surface rounded-2xl border border-border-light p-6 md:p-8 mb-6">
        <div className="flex flex-wrap gap-2 mb-4">
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${DISCIPLINE_COLORS[comp.discipline] ?? 'bg-gray-500/15 text-gray-400'}`}>
            {DISCIPLINE_LABEL[comp.discipline] ?? comp.discipline}
          </span>
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${STATUS_COLORS[comp.status] ?? 'bg-gray-500/15 text-gray-400'}`}>
            {STATUS_LABEL[comp.status] ?? comp.status}
          </span>
        </div>

        <h1 className="text-2xl md:text-3xl font-bold text-text mb-5 leading-snug">{comp.name}</h1>

        <div className="flex flex-col gap-3 text-text-muted">
          {(comp.date_start || comp.date_end) && (
            <div className="flex items-center gap-3">
              <Calendar className="w-5 h-5 shrink-0 text-primary" />
              <span>{formatDateRange(comp.date_start, comp.date_end)}</span>
            </div>
          )}
          {comp.location && (
            <div className="flex items-center gap-3">
              <MapPin className="w-5 h-5 shrink-0 text-primary" />
              <span>{comp.location}</span>
            </div>
          )}
          <div className="flex items-center gap-3">
            <Users className="w-5 h-5 shrink-0 text-primary" />
            <span>{comp.participants_count} {comp.participants_count === 1 ? 'участник зарегистрирован' : 'участников зарегистрировано'}</span>
          </div>
          {(comp.registration_open_at || comp.registration_deadline) && (
            <div className="flex items-center gap-3">
              <Clock className="w-5 h-5 shrink-0 text-primary" />
              <span>
                Приём заявок:
                {comp.registration_open_at && ` с ${new Date(comp.registration_open_at).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}`}
                {comp.registration_deadline && ` по ${new Date(comp.registration_deadline).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}`}
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="grid sm:grid-cols-3 gap-4">
        {isActive && (
          <Link
            to={`/competition/${comp.id}/register`}
            className="group bg-accent hover:bg-accent-dark text-white rounded-xl p-6 no-underline flex flex-col gap-3 transition-all shadow-lg"
          >
            <UserPlus className="w-7 h-7" />
            <div>
              <div className="font-semibold text-base">Регистрация</div>
              <div className="text-white/70 text-sm mt-0.5">Зарегистрировать участника</div>
            </div>
          </Link>
        )}

        <Link
          to={`/competition/${comp.id}/participants`}
          className="group bg-surface hover:border-primary/40 border border-border-light rounded-xl p-6 no-underline flex flex-col gap-3 transition-all"
        >
          <Users className="w-7 h-7 text-primary" />
          <div>
            <div className="font-semibold text-base text-text">Участники</div>
            <div className="text-text-muted text-sm mt-0.5">Список зарегистрированных</div>
          </div>
        </Link>

        <Link
          to={`/competition/${comp.id}/brackets`}
          className="group bg-surface hover:border-accent/40 border border-border-light rounded-xl p-6 no-underline flex flex-col gap-3 transition-all"
        >
          <Trophy className="w-7 h-7 text-accent" />
          <div>
            <div className="font-semibold text-base text-text">Турнирные сетки</div>
            <div className="text-text-muted text-sm mt-0.5">Просмотр сеток по категориям</div>
          </div>
        </Link>
      </div>
    </div>
  )
}

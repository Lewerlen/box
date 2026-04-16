import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { competitionsApi } from '../api'
import { MapPin, Calendar, Users, ChevronRight, Trophy, Clock } from 'lucide-react'

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

function DisciplineBadge({ discipline }: { discipline: string }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${DISCIPLINE_COLORS[discipline] ?? 'bg-gray-500/15 text-gray-400'}`}>
      {DISCIPLINE_LABEL[discipline] ?? discipline}
    </span>
  )
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[status] ?? 'bg-gray-500/15 text-gray-400'}`}>
      {STATUS_LABEL[status] ?? status}
    </span>
  )
}

function CompetitionCard({ comp }: { comp: Competition }) {
  return (
    <Link
      to={`/competition/${comp.id}`}
      className="group relative bg-surface rounded-xl border border-border-light hover:border-primary/40 hover:shadow-lg transition-all no-underline overflow-hidden flex flex-col"
    >
      <div className="absolute top-3 right-3 flex flex-col items-end gap-1.5">
        <DisciplineBadge discipline={comp.discipline} />
      </div>

      <div className="p-5 flex flex-col gap-3 flex-1">
        <div className="pr-24">
          <h3 className="text-base font-semibold text-text leading-snug group-hover:text-primary transition-colors">
            {comp.name}
          </h3>
        </div>

        <div className="flex flex-col gap-1.5 text-sm text-text-muted">
          {(comp.date_start || comp.date_end) && (
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 shrink-0 text-text-dim" />
              <span>{formatDateRange(comp.date_start, comp.date_end)}</span>
            </div>
          )}
          {comp.location && (
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 shrink-0 text-text-dim" />
              <span>{comp.location}</span>
            </div>
          )}
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 shrink-0 text-text-dim" />
            <span>{comp.participants_count} участников</span>
          </div>
          {(comp.registration_open_at || comp.registration_deadline) && (
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 shrink-0 text-text-dim" />
              <span className="text-xs">
                Приём заявок:
                {comp.registration_open_at && ` с ${new Date(comp.registration_open_at).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}`}
                {comp.registration_deadline && ` по ${new Date(comp.registration_deadline).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}`}
              </span>
            </div>
          )}
        </div>

        <div className="mt-auto pt-3 border-t border-border-light flex items-center justify-between">
          <StatusBadge status={comp.status} />
          <ChevronRight className="w-4 h-4 text-text-dim group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
        </div>
      </div>
    </Link>
  )
}

export default function HomePage() {
  const [competitions, setCompetitions] = useState<Competition[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    competitionsApi.getAll()
      .then((r) => setCompetitions(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const active = competitions.filter((c) => c.status === 'active' || c.status === 'upcoming')
  const finished = competitions.filter((c) => c.status === 'finished')

  return (
    <div>
      <section className="relative bg-nav overflow-x-hidden min-h-[240px] md:min-h-[300px]">
        <img
          src="/fighter-left.png"
          alt=""
          className="absolute left-0 md:left-8 bottom-0 h-48 md:h-80 opacity-15 object-contain object-bottom pointer-events-none select-none"
          style={{ filter: 'brightness(0) invert(1)' }}
        />
        <img
          src="/fighter-right.png"
          alt=""
          className="absolute right-0 md:right-8 bottom-0 h-48 md:h-80 opacity-15 object-contain object-bottom pointer-events-none select-none"
          style={{ filter: 'brightness(0) invert(1)' }}
        />
        <div className="relative max-w-7xl mx-auto px-4 py-10 md:py-14 text-center">
          <h1 className="text-3xl md:text-5xl lg:text-6xl font-bold mb-4 text-nav-text leading-tight">
            Федерация Муайтай
            <br />
            <span className="text-accent">Республики Башкортостан</span>
          </h1>
          <p className="text-nav-text-muted text-base md:text-lg max-w-2xl mx-auto">
            Регистрация участников, турнирные сетки и результаты соревнований
          </p>
        </div>
      </section>

      <div className="max-w-7xl mx-auto px-4 py-10 space-y-12">
        {loading && (
          <div className="text-center py-16 text-text-muted">Загрузка соревнований...</div>
        )}

        {!loading && competitions.length === 0 && (
          <div className="text-center py-16">
            <Trophy className="w-12 h-12 text-text-dim mx-auto mb-4" />
            <p className="text-text-muted text-lg">Соревнования пока не добавлены</p>
          </div>
        )}

        {!loading && active.length > 0 && (
          <section>
            <h2 className="text-xl font-bold text-text mb-5 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-400 inline-block" />
              Активные соревнования
            </h2>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {active.map((comp) => (
                <CompetitionCard key={comp.id} comp={comp} />
              ))}
            </div>
          </section>
        )}

        {!loading && finished.length > 0 && (
          <section>
            <h2 className="text-xl font-bold text-text mb-5 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-gray-400 inline-block" />
              Прошедшие соревнования
            </h2>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {finished.map((comp) => (
                <CompetitionCard key={comp.id} comp={comp} />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { publicApi, competitionsApi } from '../api'
import { Trophy, ChevronLeft, ChevronDown } from 'lucide-react'
import DeadlineBadge from '../components/DeadlineBadge'

interface Competition {
  id: number
  name: string
  discipline: string
  date_start: string | null
  date_end: string | null
  location: string | null
  status: 'active' | 'upcoming' | 'finished'
  participants_count: number
  registration_deadline: string | null
}

interface ApprovedBracket {
  class_name: string
  gender: string
  age_category_name: string
  weight_name: string
}

function pickBestCompetition(list: Competition[]): Competition | null {
  if (list.length === 0) return null
  const sort = (arr: Competition[]) =>
    [...arr].sort((a, b) => {
      if (!a.date_start) return 1
      if (!b.date_start) return -1
      return new Date(a.date_start).getTime() - new Date(b.date_start).getTime()
    })
  const active = list.filter(c => c.status === 'active')
  if (active.length > 0) return sort(active)[0]
  const upcoming = list.filter(c => c.status === 'upcoming')
  if (upcoming.length > 0) return sort(upcoming)[0]
  return sort(list)[0]
}

const STATUS_LABEL: Record<string, string> = {
  active: 'Идёт регистрация',
  upcoming: 'Скоро',
  finished: 'Завершено',
}

export default function BracketsPage() {
  const { id: competitionId } = useParams<{ id?: string }>()

  const [competitions, setCompetitions] = useState<Competition[]>([])
  const [selectedCompId, setSelectedCompId] = useState<number | null>(null)

  const [brackets, setBrackets] = useState<ApprovedBracket[]>([])
  const [selected, setSelected] = useState<ApprovedBracket | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!competitionId) {
      competitionsApi.getAll().then((r) => {
        const list = r.data as Competition[]
        setCompetitions(list)
        const best = pickBestCompetition(list)
        if (best) setSelectedCompId(best.id)
      }).catch(() => {})
    }
  }, [competitionId])

  const effectiveCompId = competitionId ? Number(competitionId) : (selectedCompId ?? undefined)

  useEffect(() => {
    if (!competitionId && selectedCompId === null) return
    setLoading(true)
    setSelected(null)
    publicApi.getApprovedBrackets(effectiveCompId).then((r) => {
      setBrackets(r.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [competitionId, selectedCompId])

  const selectedComp = competitions.find(c => c.id === selectedCompId)

  const grouped: Record<string, ApprovedBracket[]> = {}
  brackets.forEach((b) => {
    const key = `${b.gender} - ${b.age_category_name}`
    if (!grouped[key]) grouped[key] = []
    grouped[key].push(b)
  })

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {competitionId && (
        <Link
          to={`/competition/${competitionId}`}
          className="inline-flex items-center gap-1.5 text-sm text-text-muted hover:text-text mb-6 no-underline"
        >
          <ChevronLeft className="w-4 h-4" />
          Назад к соревнованию
        </Link>
      )}

      {!competitionId && competitions.length > 0 && (
        <div className="mb-6 bg-surface-light rounded-xl border border-border p-4">
          <label className="block text-xs font-medium text-text-muted uppercase tracking-wide mb-2">
            Соревнование
          </label>
          <div className="relative">
          <select
            value={selectedCompId ?? ''}
            onChange={(e) => {
              setSelectedCompId(e.target.value ? Number(e.target.value) : null)
            }}
            className="w-full px-3 py-2.5 pr-9 appearance-none bg-surface border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary/50"
          >
            {competitions.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}{c.status ? ` — ${STATUS_LABEL[c.status] ?? c.status}` : ''}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted pointer-events-none" />
          </div>
          {selectedComp?.status === 'active' && <DeadlineBadge deadline={selectedComp.registration_deadline} className="mt-2" />}
        </div>
      )}

      <div className="mb-6">
        <h1 className="text-2xl font-bold">Турнирные сетки</h1>
        {!competitionId && selectedComp && (
          <p className="text-text-muted text-sm mt-0.5">{selectedComp.name}</p>
        )}
      </div>

      {loading ? (
        <div className="text-center py-12 text-text-muted">Загрузка...</div>
      ) : brackets.length === 0 ? (
        <div className="text-center py-16">
          <Trophy className="w-16 h-16 mx-auto mb-4 text-text-muted" />
          <p className="text-text-muted text-lg">Утверждённых сеток пока нет</p>
          <p className="text-text-muted text-sm mt-2">Сетки появятся после утверждения администратором</p>
        </div>
      ) : (
        <div className="space-y-4">
          {Object.entries(grouped).map(([group, items]) => (
            <div key={group} className="bg-surface-light rounded-xl border border-border overflow-hidden">
              <div className="px-4 py-3 border-b border-border">
                <h3 className="font-semibold text-text">{group}</h3>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-px bg-border">
                {items.map((b, i) => (
                  <button
                    key={i}
                    onClick={() => setSelected(b)}
                    className={`bg-surface-light px-4 py-3 text-left cursor-pointer border-none hover:bg-surface-lighter/50 transition-colors ${
                      selected === b ? 'bg-primary/5 text-primary' : 'text-text'
                    }`}
                  >
                    <div className="font-medium text-sm">{b.class_name}</div>
                    <div className="text-text-muted text-xs mt-1">{b.weight_name} kg</div>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {selected && (
        <div className="mt-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold">
              {selected.class_name} - {selected.gender}, {selected.age_category_name}, {selected.weight_name} kg
            </h2>
            <button
              onClick={() => setSelected(null)}
              className="text-text-muted hover:text-text text-sm cursor-pointer bg-transparent border-none"
            >
              Закрыть
            </button>
          </div>
          <div className="bg-surface-light rounded-xl border border-border p-4 overflow-x-auto">
            <img
              src={publicApi.getBracketImage({
                class_name: selected.class_name,
                gender: selected.gender,
                age_category_name: selected.age_category_name,
                weight_name: selected.weight_name,
                competition_id: effectiveCompId,
              })}
              alt="Турнирная сетка"
              className="max-w-full"
            />
          </div>
        </div>
      )}
    </div>
  )
}

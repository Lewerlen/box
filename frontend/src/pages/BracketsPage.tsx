import { useEffect, useMemo, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { publicApi, competitionsApi } from '../api'
import { Trophy, ChevronLeft, ChevronDown, Clock, CheckCircle2, Users, Info, X, Maximize2 } from 'lucide-react'
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

interface Category {
  class_name: string
  gender: string
  age_category_name: string
  weight_name: string
  participant_count: number
  approved: boolean
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

function weightSortKey(w: string): number {
  const m = String(w).match(/[\d.]+/)
  return m ? parseFloat(m[0]) : 0
}

export default function BracketsPage() {
  const { id: competitionId } = useParams<{ id?: string }>()

  const [competitions, setCompetitions] = useState<Competition[]>([])
  const [selectedCompId, setSelectedCompId] = useState<number | null>(null)

  const [categories, setCategories] = useState<Category[]>([])
  const [selected, setSelected] = useState<Category | null>(null)
  const [loading, setLoading] = useState(true)
  const [zoom, setZoom] = useState(false)

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
    publicApi.getBracketCategories(effectiveCompId).then((r) => {
      setCategories(r.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [competitionId, selectedCompId])

  const selectedComp = competitions.find(c => c.id === selectedCompId)

  const totals = useMemo(() => {
    const approved = categories.filter(c => c.approved).length
    return { total: categories.length, approved, pending: categories.length - approved }
  }, [categories])

  const grouped = useMemo(() => {
    const map = new Map<string, Category[]>()
    for (const c of categories) {
      const key = `${c.gender} · ${c.age_category_name}`
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(c)
    }
    const sortedEntries = Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0], 'ru'))
    return sortedEntries.map(([key, items]) => [
      key,
      items.sort((a, b) =>
        a.class_name.localeCompare(b.class_name, 'ru') ||
        weightSortKey(a.weight_name) - weightSortKey(b.weight_name)
      ),
    ] as [string, Category[]])
  }, [categories])

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
              onChange={(e) => setSelectedCompId(e.target.value ? Number(e.target.value) : null)}
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

      <div className="mb-4">
        <h1 className="text-2xl font-bold">Турнирные сетки</h1>
        {!competitionId && selectedComp && (
          <p className="text-text-muted text-sm mt-0.5">{selectedComp.name}</p>
        )}
      </div>

      {/* Help & status banner */}
      {!loading && categories.length > 0 && (
        <div className="bg-accent/5 border border-accent/20 rounded-xl px-4 py-3 mb-6 flex items-start gap-3">
          <Info className="w-5 h-5 text-accent shrink-0 mt-0.5" />
          <div className="text-sm text-text-secondary leading-relaxed flex-1">
            <span className="text-text font-medium">Категории формируются автоматически</span> из списка зарегистрированных участников: класс мастерства · пол · возраст · вес. Сетку можно открыть только после того, как администратор её утвердит.
            <div className="flex flex-wrap gap-3 mt-2 text-xs">
              <span className="inline-flex items-center gap-1 text-text-muted">
                Всего категорий: <span className="text-text font-semibold">{totals.total}</span>
              </span>
              <span className="inline-flex items-center gap-1 text-success">
                <CheckCircle2 className="w-3.5 h-3.5" /> Утверждено: <span className="font-semibold">{totals.approved}</span>
              </span>
              <span className="inline-flex items-center gap-1 text-text-muted">
                <Clock className="w-3.5 h-3.5" /> В обработке: <span className="font-semibold">{totals.pending}</span>
              </span>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-text-muted">Загрузка...</div>
      ) : categories.length === 0 ? (
        <div className="text-center py-16">
          <Trophy className="w-16 h-16 mx-auto mb-4 text-text-muted" />
          <p className="text-text-muted text-lg">Категорий пока нет</p>
          <p className="text-text-muted text-sm mt-2">Они появятся, как только участники начнут регистрироваться</p>
        </div>
      ) : (
        <div className="space-y-4">
          {grouped.map(([group, items]) => (
            <div key={group} className="bg-surface-light rounded-xl border border-border overflow-hidden">
              <div className="px-4 py-3 border-b border-border flex items-center justify-between">
                <h3 className="font-semibold text-text">{group}</h3>
                <span className="text-xs text-text-muted">{items.length} {items.length === 1 ? 'категория' : 'категорий'}</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 p-3">
                {items.map((c, i) => {
                  const isSelected = selected
                    && selected.class_name === c.class_name
                    && selected.gender === c.gender
                    && selected.age_category_name === c.age_category_name
                    && selected.weight_name === c.weight_name
                  return (
                    <button
                      key={i}
                      onClick={() => c.approved && setSelected(c)}
                      disabled={!c.approved}
                      title={c.approved ? 'Открыть сетку' : 'Сетка ещё не утверждена администратором'}
                      className={`text-left px-3 py-3 rounded-lg border transition-all bg-surface ${
                        c.approved
                          ? 'cursor-pointer hover:border-primary/50 hover:bg-primary/5'
                          : 'cursor-not-allowed opacity-70'
                      } ${isSelected ? 'border-primary bg-primary/10' : 'border-border'}`}
                    >
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-primary/15 text-primary text-xs font-bold shrink-0">
                            {c.class_name.charAt(0)}
                          </span>
                          <div className="min-w-0">
                            <div className="text-sm font-semibold text-text truncate">{c.class_name}</div>
                            <div className="text-xs text-text-muted">{c.weight_name}</div>
                          </div>
                        </div>
                        {c.approved ? (
                          <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-success/15 text-success font-semibold whitespace-nowrap">
                            <CheckCircle2 className="w-3 h-3" /> Утверждена
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-text-muted/15 text-text-muted font-semibold whitespace-nowrap">
                            <Clock className="w-3 h-3" /> Готовится
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1.5 text-xs text-text-muted">
                        <Users className="w-3.5 h-3.5" />
                        <span>{c.participant_count} {c.participant_count === 1 ? 'участник' : c.participant_count < 5 ? 'участника' : 'участников'}</span>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {selected && (
        <div className="mt-8 bg-surface-light rounded-xl border border-border overflow-hidden">
          <div className="px-4 py-3 border-b border-border flex flex-wrap items-center gap-3 justify-between">
            <div className="flex flex-wrap items-center gap-2 min-w-0">
              <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-primary/15 text-primary text-xs font-bold">
                {selected.class_name.charAt(0)}
              </span>
              <h2 className="text-base font-semibold text-text">
                {selected.class_name}
              </h2>
              <span className="text-xs text-text-muted">·</span>
              <span className="text-sm text-text-muted">{selected.gender}</span>
              <span className="text-xs text-text-muted">·</span>
              <span className="text-sm text-text-muted">{selected.age_category_name}</span>
              <span className="text-xs text-text-muted">·</span>
              <span className="text-sm text-text-muted">{selected.weight_name}</span>
              <span className="inline-flex items-center gap-1 text-xs text-text-muted ml-2">
                <Users className="w-3.5 h-3.5" /> {selected.participant_count}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setZoom(true)}
                className="inline-flex items-center gap-1.5 text-sm text-text-muted hover:text-text cursor-pointer bg-transparent border-none"
                title="На весь экран"
              >
                <Maximize2 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setSelected(null)}
                className="inline-flex items-center gap-1 text-sm text-text-muted hover:text-text cursor-pointer bg-transparent border-none"
              >
                <X className="w-4 h-4" /> Закрыть
              </button>
            </div>
          </div>
          <div className="p-4 overflow-x-auto bg-surface">
            <img
              src={publicApi.getBracketImage({
                class_name: selected.class_name,
                gender: selected.gender,
                age_category_name: selected.age_category_name,
                weight_name: selected.weight_name,
                competition_id: effectiveCompId,
              })}
              alt="Турнирная сетка"
              className="max-w-full mx-auto"
            />
          </div>
        </div>
      )}

      {selected && zoom && (
        <div
          className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
          onClick={() => setZoom(false)}
        >
          <button
            onClick={(e) => { e.stopPropagation(); setZoom(false) }}
            className="absolute top-4 right-4 text-white bg-transparent border-none cursor-pointer p-2"
          >
            <X className="w-6 h-6" />
          </button>
          <img
            src={publicApi.getBracketImage({
              class_name: selected.class_name,
              gender: selected.gender,
              age_category_name: selected.age_category_name,
              weight_name: selected.weight_name,
              competition_id: effectiveCompId,
            })}
            alt="Турнирная сетка"
            className="max-w-full max-h-full bg-white rounded-lg"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  )
}

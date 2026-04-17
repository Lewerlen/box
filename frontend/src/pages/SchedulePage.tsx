import { useEffect, useMemo, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { publicApi, competitionsApi } from '../api'
import { Calendar, ChevronLeft, MapPin, Search, X } from 'lucide-react'

interface Fighter {
  id: number
  fio: string
  club_name: string | null
  city_name: string | null
  region_name: string | null
}

interface Fight {
  id: number
  ring_id: number
  day_number: number
  fight_order: number
  class_name: string
  gender: string
  age_category_name: string
  weight_name: string
  round_label: string
  fighter1: Fighter | null
  fighter2: Fighter | null
}

interface Ring { id: number; name: string; sort_order: number }
interface Day { day_number: number; date: string | null }

interface Competition {
  id: number
  name: string
  date_start: string | null
  date_end: string | null
  location: string | null
}

function formatDateShort(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })
}

function fighterLine(f: Fighter | null): { name: string; sub: string } {
  if (!f) return { name: '—', sub: '' }
  const parts = [f.region_name, f.city_name, f.club_name].filter(Boolean)
  return { name: f.fio, sub: parts.join(', ') }
}

export default function SchedulePage() {
  const { id } = useParams<{ id: string }>()
  const competitionId = Number(id)

  const [comp, setComp] = useState<Competition | null>(null)
  const [days, setDays] = useState<Day[]>([])
  const [rings, setRings] = useState<Ring[]>([])
  const [fights, setFights] = useState<Fight[]>([])
  const [loading, setLoading] = useState(true)
  const [activeDay, setActiveDay] = useState<number | null>(null)
  const [activeRing, setActiveRing] = useState<number | null>(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    if (!competitionId) return
    competitionsApi.getById(competitionId).then((r) => setComp(r.data)).catch(() => {})
    publicApi.getSchedule(competitionId).then((r) => {
      setDays(r.data.days || [])
      setRings(r.data.rings || [])
      setFights(r.data.fights || [])
      const firstDay = r.data.days?.[0]?.day_number ?? null
      setActiveDay(firstDay)
      const firstRing = r.data.rings?.[0]?.id ?? null
      setActiveRing(firstRing)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [competitionId])

  const fightsForCell = useMemo(() => {
    if (activeDay === null || activeRing === null) return []
    return fights
      .filter((f) => f.day_number === activeDay && f.ring_id === activeRing)
      .sort((a, b) => a.fight_order - b.fight_order)
  }, [fights, activeDay, activeRing])

  const ringNameById = useMemo(() => {
    const m = new Map<number, string>()
    rings.forEach((r) => m.set(r.id, r.name))
    return m
  }, [rings])

  const dateByDay = useMemo(() => {
    const m = new Map<number, string | null>()
    days.forEach((d) => m.set(d.day_number, d.date))
    return m
  }, [days])

  const searchResults = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return [] as Array<Fight & { _orderInCell: number }>
    const list: Array<Fight & { _orderInCell: number }> = []
    const ordered = [...fights].sort((a, b) =>
      a.day_number - b.day_number ||
      (rings.findIndex(r => r.id === a.ring_id) - rings.findIndex(r => r.id === b.ring_id)) ||
      a.fight_order - b.fight_order
    )
    const cellCounter = new Map<string, number>()
    for (const f of ordered) {
      const ck = `${f.day_number}|${f.ring_id}`
      const next = (cellCounter.get(ck) ?? 0) + 1
      cellCounter.set(ck, next)
      const a = (f.fighter1?.fio ?? '').toLowerCase()
      const b = (f.fighter2?.fio ?? '').toLowerCase()
      if (a.includes(q) || b.includes(q)) {
        list.push({ ...f, _orderInCell: next })
      }
    }
    return list
  }, [search, fights, rings])

  if (loading) return <div className="text-center py-12 text-text-muted">Загрузка...</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <Link to={`/competition/${competitionId}`} className="inline-flex items-center gap-1.5 text-sm text-text-muted hover:text-text mb-6 no-underline">
        <ChevronLeft className="w-4 h-4" /> Назад к соревнованию
      </Link>

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text">Расписание боёв</h1>
        {comp && <p className="text-text-muted text-sm mt-1">{comp.name}</p>}
        {comp?.location && (
          <p className="inline-flex items-center gap-1.5 text-text-muted text-sm mt-1">
            <MapPin className="w-4 h-4" /> {comp.location}
          </p>
        )}
      </div>

      {fights.length === 0 ? (
        <div className="text-center py-16">
          <Calendar className="w-16 h-16 mx-auto mb-4 text-text-muted" />
          <p className="text-text-muted text-lg">Расписание пока не опубликовано</p>
          <p className="text-text-muted text-sm mt-2">Бои появятся, когда модератор распределит пары</p>
        </div>
      ) : (
        <>
          {/* Personal search */}
          <div className="bg-surface-light border border-border rounded-xl p-4 mb-6">
            <label className="text-sm font-semibold text-text mb-2 block">Найти свои бои</label>
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Введите фамилию участника"
                className="w-full pl-9 pr-9 py-2.5 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary/40"
              />
              {search && (
                <button onClick={() => setSearch('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-text-muted hover:text-text bg-transparent border-none cursor-pointer p-1">
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
            {search.trim() && (
              <div className="mt-3">
                {searchResults.length === 0 ? (
                  <p className="text-text-muted text-sm py-2">Бои с таким участником не найдены. Возможно, расписание ещё не составлено.</p>
                ) : (
                  <div className="space-y-2">
                    <p className="text-xs text-text-muted">Найдено: {searchResults.length}</p>
                    {searchResults.map((f) => {
                      const a = fighterLine(f.fighter1)
                      const b = fighterLine(f.fighter2)
                      const dDate = dateByDay.get(f.day_number)
                      return (
                        <button
                          key={f.id}
                          onClick={() => { setActiveDay(f.day_number); setActiveRing(f.ring_id); setSearch('') }}
                          className="w-full text-left bg-surface border border-border hover:border-primary/40 rounded-lg p-3 cursor-pointer transition-colors"
                        >
                          <div className="flex flex-wrap items-center gap-2 mb-2">
                            <span className="px-2 py-0.5 rounded-full bg-primary/15 text-primary text-xs font-semibold">День {f.day_number}{dDate ? ` / ${formatDateShort(dDate)}` : ''}</span>
                            <span className="px-2 py-0.5 rounded-full bg-accent/15 text-accent text-xs font-semibold">{ringNameById.get(f.ring_id) ?? '—'}</span>
                            <span className="px-2 py-0.5 rounded-full bg-surface-light text-text border border-border text-xs font-semibold">Бой № {f._orderInCell}</span>
                            <span className="text-xs text-text-muted">{f.class_name} · {f.gender} · {f.age_category_name} · {f.weight_name} кг</span>
                          </div>
                          <div className="text-sm text-text">
                            <span className="font-medium">{a.name}</span>
                            <span className="text-text-muted mx-2">vs</span>
                            <span className="font-medium">{b.name}</span>
                          </div>
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            )}
          </div>

          {days.length > 0 && (
            <div className="flex gap-2 mb-6 border-b border-border overflow-x-auto">
              {days.map((d) => (
                <button
                  key={d.day_number}
                  onClick={() => setActiveDay(d.day_number)}
                  className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors cursor-pointer bg-transparent whitespace-nowrap ${
                    activeDay === d.day_number ? 'border-primary text-primary' : 'border-transparent text-text-muted hover:text-text'
                  }`}
                >
                  День {d.day_number}{d.date ? ` / ${formatDateShort(d.date)}` : ''}
                </button>
              ))}
            </div>
          )}

          <div className="grid md:grid-cols-[200px_1fr] gap-6">
            <div className="space-y-1">
              <div className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-2">Ринги</div>
              {rings.map((r) => (
                <button
                  key={r.id}
                  onClick={() => setActiveRing(r.id)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg text-sm border transition-all cursor-pointer ${
                    activeRing === r.id
                      ? 'bg-primary/10 border-primary/30 text-primary font-medium'
                      : 'bg-surface-light border-border hover:border-primary/30 text-text'
                  }`}
                >
                  {r.name}
                </button>
              ))}
            </div>

            <div>
              {fightsForCell.length === 0 ? (
                <div className="bg-surface-light rounded-xl border border-border p-8 text-center text-text-muted">
                  Нет боёв в выбранной комбинации дня и ринга
                </div>
              ) : (
                <div className="space-y-3">
                  {fightsForCell.map((f, idx) => {
                    const a = fighterLine(f.fighter1)
                    const b = fighterLine(f.fighter2)
                    return (
                      <div key={f.id} className="bg-surface-light rounded-xl border border-border p-4">
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2 text-xs">
                            <span className="px-2 py-0.5 rounded-full bg-primary/15 text-primary font-semibold">№ {idx + 1}</span>
                            <span className="text-text-muted">{f.class_name} · {f.gender} · {f.age_category_name}</span>
                          </div>
                          <div className="flex items-center gap-2 text-xs">
                            <span className="px-2 py-0.5 rounded-full bg-surface text-text-muted border border-border">{f.weight_name} kg</span>
                            {f.round_label && <span className="px-2 py-0.5 rounded-full bg-accent/15 text-accent">{f.round_label}</span>}
                          </div>
                        </div>
                        <div className="grid sm:grid-cols-[1fr_auto_1fr] gap-3 items-center">
                          <div className="text-text">
                            <div className="font-semibold">{a.name}</div>
                            {a.sub && <div className="text-xs text-text-muted mt-0.5">{a.sub}</div>}
                          </div>
                          <div className="text-text-muted text-sm font-bold text-center">VS</div>
                          <div className="text-text sm:text-right">
                            <div className="font-semibold">{b.name}</div>
                            {b.sub && <div className="text-xs text-text-muted mt-0.5">{b.sub}</div>}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

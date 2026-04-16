import { useCallback, useEffect, useMemo, useState } from 'react'
import { adminApi } from '../../api'
import { Plus, Pencil, Trash2, Check, X, ArrowRight, Loader2, GripVertical } from 'lucide-react'

interface Ring { id: number; name: string; sort_order: number }
interface Day { day_number: number; date: string | null }

interface Pair {
  pair_key: string
  class_name: string
  gender: string
  age_category_name: string
  weight_name: string
  round_label: string
  slot_index: number
  fighter1_id: number
  fighter2_id: number
  fighter1: { id: number; fio: string; club_name: string | null; city_name: string | null }
  fighter2: { id: number; fio: string; club_name: string | null; city_name: string | null }
  scheduled: boolean
}

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
  fighter1_id: number
  fighter2_id: number
  fighter1: Fighter | null
  fighter2: Fighter | null
}

function shortFighter(f: { fio: string; club_name: string | null }) {
  return f.club_name ? `${f.fio} (${f.club_name})` : f.fio
}

function formatDateShort(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })
}

interface DragData {
  type: 'pair' | 'fight'
  pair?: Pair
  fightId?: number
}

export default function AdminSchedule({ competitionId }: { competitionId: number }) {
  const [rings, setRings] = useState<Ring[]>([])
  const [days, setDays] = useState<Day[]>([])
  const [fights, setFights] = useState<Fight[]>([])
  const [pairs, setPairs] = useState<Pair[]>([])
  const [loading, setLoading] = useState(true)
  const [filterClass, setFilterClass] = useState('')
  const [filterAge, setFilterAge] = useState('')
  const [filterWeight, setFilterWeight] = useState('')
  const [selectedFights, setSelectedFights] = useState<Set<number>>(new Set())
  const [drag, setDrag] = useState<DragData | null>(null)
  const [busy, setBusy] = useState(false)

  // Rings management
  const [newRingName, setNewRingName] = useState('')
  const [editingRing, setEditingRing] = useState<number | null>(null)
  const [editRingName, setEditRingName] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [r1, r2, r3] = await Promise.all([
        adminApi.getRings(competitionId),
        adminApi.getAdminSchedule(competitionId),
        adminApi.getSchedulePairs(competitionId),
      ])
      setRings(r1.data)
      setDays(r2.data.days || [])
      setFights(r2.data.fights || [])
      setPairs(r3.data)
    } catch {}
    setLoading(false)
  }, [competitionId])

  useEffect(() => { load() }, [load])

  const filtered = useMemo(() => {
    return pairs.filter((p) => {
      if (p.scheduled) return false
      if (filterClass && p.class_name !== filterClass) return false
      if (filterAge && p.age_category_name !== filterAge) return false
      if (filterWeight && p.weight_name !== filterWeight) return false
      return true
    })
  }, [pairs, filterClass, filterAge, filterWeight])

  const classOptions = useMemo(() => Array.from(new Set(pairs.map((p) => p.class_name))).sort(), [pairs])
  const ageOptions = useMemo(() => Array.from(new Set(pairs.map((p) => p.age_category_name))).sort(), [pairs])
  const weightOptions = useMemo(() => Array.from(new Set(pairs.map((p) => p.weight_name))).sort(), [pairs])

  // ----- Rings ops -----
  const addRing = async () => {
    const name = newRingName.trim()
    if (!name) return
    setBusy(true)
    try {
      await adminApi.createRing(competitionId, name)
      setNewRingName('')
      await load()
    } catch {}
    setBusy(false)
  }

  const renameRing = async (id: number) => {
    const name = editRingName.trim()
    if (!name) return
    setBusy(true)
    try {
      await adminApi.updateRing(id, { name })
      setEditingRing(null)
      await load()
    } catch {}
    setBusy(false)
  }

  const deleteRing = async (id: number) => {
    if (!confirm('Удалить ринг и все связанные с ним бои?')) return
    setBusy(true)
    try {
      await adminApi.deleteRing(id)
      await load()
    } catch {}
    setBusy(false)
  }

  const moveRingPos = async (id: number, dir: -1 | 1) => {
    const ids = rings.map((r) => r.id)
    const idx = ids.indexOf(id)
    if (idx < 0) return
    const next = idx + dir
    if (next < 0 || next >= ids.length) return
    ;[ids[idx], ids[next]] = [ids[next], ids[idx]]
    setBusy(true)
    try {
      await adminApi.reorderRings(competitionId, ids)
      await load()
    } catch {}
    setBusy(false)
  }

  // ----- Drop targets -----
  const dropOnCell = async (ringId: number, dayNumber: number) => {
    if (!drag) return
    setBusy(true)
    try {
      if (drag.type === 'pair' && drag.pair) {
        await adminApi.createFight(competitionId, {
          ring_id: ringId,
          day_number: dayNumber,
          fighter1_id: drag.pair.fighter1_id,
          fighter2_id: drag.pair.fighter2_id,
          class_name: drag.pair.class_name,
          gender: drag.pair.gender,
          age_category_name: drag.pair.age_category_name,
          weight_name: drag.pair.weight_name,
          round_label: drag.pair.round_label,
        })
      } else if (drag.type === 'fight' && drag.fightId) {
        await adminApi.updateFight(drag.fightId, { ring_id: ringId, day_number: dayNumber })
      }
      await load()
    } catch {}
    setDrag(null)
    setBusy(false)
  }

  const removeFight = async (id: number) => {
    setBusy(true)
    try {
      await adminApi.deleteFight(id)
      await load()
    } catch {}
    setBusy(false)
  }

  const moveFightInCell = async (ringId: number, dayNumber: number, fightId: number, direction: -1 | 1) => {
    const cellFights = fights
      .filter((f) => f.ring_id === ringId && f.day_number === dayNumber)
      .sort((a, b) => a.fight_order - b.fight_order)
    const idx = cellFights.findIndex((f) => f.id === fightId)
    if (idx < 0) return
    const ni = idx + direction
    if (ni < 0 || ni >= cellFights.length) return
    const ids = cellFights.map((f) => f.id)
    ;[ids[idx], ids[ni]] = [ids[ni], ids[idx]]
    setBusy(true)
    try {
      await adminApi.reorderFightsInCell(competitionId, ringId, dayNumber, ids)
      await load()
    } catch {}
    setBusy(false)
  }

  const moveRingToNextDay = async (ringId: number, dayNumber: number) => {
    setBusy(true)
    try {
      await adminApi.moveRingToNextDay(competitionId, ringId, dayNumber)
      await load()
    } catch {}
    setBusy(false)
  }

  const bulkMove = async (ringId: number, dayNumber: number) => {
    if (selectedFights.size === 0) return
    setBusy(true)
    try {
      await adminApi.bulkMoveFights(competitionId, Array.from(selectedFights), ringId, dayNumber)
      setSelectedFights(new Set())
      await load()
    } catch {}
    setBusy(false)
  }

  const toggleSelect = (id: number) => {
    const next = new Set(selectedFights)
    if (next.has(id)) next.delete(id); else next.add(id)
    setSelectedFights(next)
  }

  const effectiveDays: Day[] = useMemo(() => {
    const map = new Map<number, Day>()
    for (const d of days) map.set(d.day_number, d)
    for (const f of fights) {
      if (!map.has(f.day_number)) map.set(f.day_number, { day_number: f.day_number, date: null })
    }
    if (map.size === 0) map.set(1, { day_number: 1, date: null })
    return Array.from(map.values()).sort((a, b) => a.day_number - b.day_number)
  }, [days, fights])

  if (loading) return <div className="text-center py-12 text-text-muted">Загрузка...</div>

  return (
    <div className="space-y-6">
      {/* Rings management */}
      <div className="bg-surface-light rounded-xl border border-border p-5">
        <h3 className="text-sm font-semibold text-text-secondary mb-3">Ринги</h3>
        <div className="flex flex-wrap gap-2 mb-3">
          {rings.map((r, i) => (
            <div key={r.id} className="flex items-center gap-1 bg-surface border border-border rounded-lg px-2 py-1">
              <button onClick={() => moveRingPos(r.id, -1)} disabled={busy || i === 0}
                className="text-text-muted hover:text-text disabled:opacity-30 cursor-pointer bg-transparent border-none px-1">‹</button>
              {editingRing === r.id ? (
                <>
                  <input value={editRingName} onChange={(e) => setEditRingName(e.target.value)}
                    className="px-2 py-0.5 bg-surface border border-border rounded text-sm w-32" />
                  <button onClick={() => renameRing(r.id)} disabled={busy}
                    className="text-success cursor-pointer bg-transparent border-none p-1"><Check className="w-3.5 h-3.5" /></button>
                  <button onClick={() => setEditingRing(null)}
                    className="text-text-muted cursor-pointer bg-transparent border-none p-1"><X className="w-3.5 h-3.5" /></button>
                </>
              ) : (
                <>
                  <span className="text-sm text-text px-1">{r.name}</span>
                  <button onClick={() => { setEditingRing(r.id); setEditRingName(r.name) }}
                    className="text-text-muted hover:text-text cursor-pointer bg-transparent border-none p-1"><Pencil className="w-3.5 h-3.5" /></button>
                  <button onClick={() => deleteRing(r.id)} disabled={busy}
                    className="text-danger cursor-pointer bg-transparent border-none p-1"><Trash2 className="w-3.5 h-3.5" /></button>
                </>
              )}
              <button onClick={() => moveRingPos(r.id, 1)} disabled={busy || i === rings.length - 1}
                className="text-text-muted hover:text-text disabled:opacity-30 cursor-pointer bg-transparent border-none px-1">›</button>
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <input value={newRingName} onChange={(e) => setNewRingName(e.target.value)}
            placeholder="Название ринга, например «Ринг А»"
            className="flex-1 px-3 py-2 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none" />
          <button onClick={addRing} disabled={busy || !newRingName.trim()}
            className="flex items-center gap-1.5 px-3 py-2 bg-primary hover:bg-primary-dark text-white rounded-lg text-sm cursor-pointer border-none disabled:opacity-50">
            <Plus className="w-4 h-4" /> Добавить
          </button>
        </div>
      </div>

      {rings.length === 0 ? (
        <div className="bg-surface-light rounded-xl border border-border p-8 text-center text-text-muted">
          Сначала добавьте хотя бы один ринг, чтобы начать составлять расписание.
        </div>
      ) : (
        <div className="grid lg:grid-cols-[320px_1fr] gap-6">
          {/* Pool of unscheduled pairs */}
          <div className="bg-surface-light rounded-xl border border-border p-4">
            <h3 className="text-sm font-semibold text-text-secondary mb-3">
              Нераспределённые пары <span className="text-text-muted">({filtered.length})</span>
            </h3>
            <div className="grid grid-cols-1 gap-2 mb-3">
              <select value={filterClass} onChange={(e) => setFilterClass(e.target.value)}
                className="px-2 py-1.5 bg-surface border border-border rounded text-sm text-text">
                <option value="">Все классы</option>
                {classOptions.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
              <select value={filterAge} onChange={(e) => setFilterAge(e.target.value)}
                className="px-2 py-1.5 bg-surface border border-border rounded text-sm text-text">
                <option value="">Все возраста</option>
                {ageOptions.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
              <select value={filterWeight} onChange={(e) => setFilterWeight(e.target.value)}
                className="px-2 py-1.5 bg-surface border border-border rounded text-sm text-text">
                <option value="">Все веса</option>
                {weightOptions.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-1">
              {filtered.length === 0 && (
                <p className="text-text-muted text-sm py-4 text-center">Все пары распределены</p>
              )}
              {filtered.map((p) => (
                <div key={p.pair_key} draggable
                  onDragStart={() => setDrag({ type: 'pair', pair: p })}
                  onDragEnd={() => setDrag(null)}
                  className="bg-surface border border-border rounded-lg p-2.5 cursor-grab active:cursor-grabbing hover:border-primary/40 transition-colors">
                  <div className="flex items-center justify-between text-xs text-text-muted mb-1">
                    <span>{p.class_name} · {p.gender} · {p.age_category_name}</span>
                    <span className="px-1.5 py-0.5 rounded bg-accent/15 text-accent">{p.round_label}</span>
                  </div>
                  <div className="text-sm text-text">
                    <div className="font-medium">{shortFighter(p.fighter1)}</div>
                    <div className="text-text-muted text-xs">vs</div>
                    <div className="font-medium">{shortFighter(p.fighter2)}</div>
                    <div className="text-xs text-text-muted mt-1">{p.weight_name} kg</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Schedule grid */}
          <div className="overflow-x-auto">
            {selectedFights.size > 0 && (
              <div className="bg-accent/10 border border-accent/30 rounded-lg px-3 py-2 mb-3 text-sm flex items-center justify-between">
                <span className="text-accent">Выбрано: {selectedFights.size}</span>
                <button onClick={() => setSelectedFights(new Set())} className="text-text-muted hover:text-text cursor-pointer bg-transparent border-none text-xs">Снять выделение</button>
              </div>
            )}
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className="text-left p-2 text-xs text-text-muted font-medium border-b border-border">Ринг</th>
                  {effectiveDays.map((d) => (
                    <th key={d.day_number} className="text-left p-2 text-xs text-text-muted font-medium border-b border-border min-w-[260px]">
                      День {d.day_number}{d.date ? ` / ${formatDateShort(d.date)}` : ''}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rings.map((r) => (
                  <tr key={r.id}>
                    <td className="align-top p-2 text-sm font-medium text-text border-b border-border">{r.name}</td>
                    {effectiveDays.map((d) => {
                      const cellFights = fights
                        .filter((f) => f.ring_id === r.id && f.day_number === d.day_number)
                        .sort((a, b) => a.fight_order - b.fight_order)
                      return (
                        <td key={d.day_number}
                          onDragOver={(e) => e.preventDefault()}
                          onDrop={(e) => { e.preventDefault(); dropOnCell(r.id, d.day_number) }}
                          className="align-top p-1.5 border-b border-border">
                          <div className="space-y-1.5 min-h-[60px]">
                            {cellFights.map((f, idx) => {
                              const sel = selectedFights.has(f.id)
                              return (
                                <div key={f.id} draggable
                                  onDragStart={() => setDrag({ type: 'fight', fightId: f.id })}
                                  onDragEnd={() => setDrag(null)}
                                  className={`group rounded-lg p-2 text-xs cursor-grab active:cursor-grabbing border transition-colors ${
                                    sel ? 'bg-accent/15 border-accent/50' : 'bg-surface border-border hover:border-primary/30'
                                  }`}>
                                  <div className="flex items-center gap-1.5">
                                    <input type="checkbox" checked={sel} onChange={() => toggleSelect(f.id)}
                                      className="cursor-pointer" />
                                    <GripVertical className="w-3 h-3 text-text-muted" />
                                    <span className="text-text-muted">№{idx + 1}</span>
                                    <span className="px-1.5 py-0.5 rounded bg-accent/15 text-accent">{f.round_label}</span>
                                    <span className="text-text-muted truncate flex-1">{f.class_name} · {f.weight_name}</span>
                                    <button onClick={() => moveFightInCell(r.id, d.day_number, f.id, -1)} disabled={busy || idx === 0}
                                      className="text-text-muted hover:text-text disabled:opacity-30 cursor-pointer bg-transparent border-none px-1">↑</button>
                                    <button onClick={() => moveFightInCell(r.id, d.day_number, f.id, 1)} disabled={busy || idx === cellFights.length - 1}
                                      className="text-text-muted hover:text-text disabled:opacity-30 cursor-pointer bg-transparent border-none px-1">↓</button>
                                    <button onClick={() => removeFight(f.id)} disabled={busy}
                                      className="text-danger opacity-0 group-hover:opacity-100 cursor-pointer bg-transparent border-none p-0.5">
                                      <Trash2 className="w-3 h-3" />
                                    </button>
                                  </div>
                                  <div className="text-text mt-1">
                                    <div className="truncate">{f.fighter1?.fio ?? '—'} <span className="text-text-muted">{f.fighter1?.club_name ?? ''}</span></div>
                                    <div className="truncate">{f.fighter2?.fio ?? '—'} <span className="text-text-muted">{f.fighter2?.club_name ?? ''}</span></div>
                                  </div>
                                </div>
                              )
                            })}
                            <div className="flex items-center gap-2 pt-1">
                              {cellFights.length > 0 && (
                                <button onClick={() => moveRingToNextDay(r.id, d.day_number)} disabled={busy}
                                  className="text-xs text-text-muted hover:text-primary cursor-pointer bg-transparent border-none flex items-center gap-1">
                                  <ArrowRight className="w-3 h-3" /> На следующий день
                                </button>
                              )}
                              {selectedFights.size > 0 && (
                                <button onClick={() => bulkMove(r.id, d.day_number)} disabled={busy}
                                  className="text-xs text-accent hover:underline cursor-pointer bg-transparent border-none">
                                  Перенести выбранное сюда
                                </button>
                              )}
                            </div>
                          </div>
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {busy && (
        <div className="fixed bottom-6 right-6 bg-surface-light border border-border rounded-lg px-4 py-2 flex items-center gap-2 text-sm text-text-muted shadow-lg">
          <Loader2 className="w-4 h-4 animate-spin" /> Обновление...
        </div>
      )}
    </div>
  )
}

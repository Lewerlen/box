import { useCallback, useEffect, useMemo, useState } from 'react'
import { adminApi } from '../../api'
import { Plus, Pencil, Trash2, Check, X, ArrowRight, Loader2, GripVertical, Info, ChevronDown, ChevronRight } from 'lucide-react'

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

  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({})

  const groupedPairs = useMemo(() => {
    const map = new Map<string, { key: string; title: string; subtitle: string; items: Pair[] }>()
    for (const p of filtered) {
      const key = `${p.class_name}|${p.gender}|${p.age_category_name}|${p.weight_name}`
      if (!map.has(key)) {
        map.set(key, {
          key,
          title: `${p.class_name} · ${p.gender} · ${p.age_category_name}`,
          subtitle: `${p.weight_name} кг`,
          items: [],
        })
      }
      map.get(key)!.items.push(p)
    }
    return Array.from(map.values()).sort((a, b) => a.title.localeCompare(b.title, 'ru'))
  }, [filtered])

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

  const totalScheduled = fights.length
  const totalUnscheduled = pairs.filter(p => !p.scheduled).length

  return (
    <div className="space-y-6">
      {/* Help banner */}
      <div className="bg-accent/5 border border-accent/20 rounded-xl px-4 py-3 flex items-start gap-3">
        <Info className="w-5 h-5 text-accent shrink-0 mt-0.5" />
        <div className="text-sm text-text-secondary leading-relaxed">
          <span className="text-text font-medium">Как составить расписание:</span> добавьте ринги, затем перетащите карточки пар из левой колонки в нужную ячейку «Ринг × День». Бои внутри ячейки переставляются стрелками ↑↓, между ячейками — обычным перетаскиванием.
          <span className="text-text-muted ml-1">Распределено: <span className="text-text font-medium">{totalScheduled}</span> из <span className="text-text font-medium">{totalScheduled + totalUnscheduled}</span></span>
        </div>
      </div>

      {/* Rings management */}
      <div className="bg-surface-light rounded-xl border border-border p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">Ринги ({rings.length})</h3>
        </div>
        {rings.length === 0 ? (
          <p className="text-text-muted text-sm mb-3">Пока нет рингов. Добавьте хотя бы один, чтобы начать.</p>
        ) : (
          <div className="flex flex-wrap gap-2 mb-3">
            {rings.map((r, i) => (
              <div key={r.id} className="flex items-center gap-1 bg-primary/5 border border-primary/20 rounded-lg px-2 py-1.5">
                <button onClick={() => moveRingPos(r.id, -1)} disabled={busy || i === 0}
                  className="text-text-muted hover:text-text disabled:opacity-30 cursor-pointer bg-transparent border-none px-1" title="Влево">‹</button>
                {editingRing === r.id ? (
                  <>
                    <input value={editRingName} onChange={(e) => setEditRingName(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') renameRing(r.id); if (e.key === 'Escape') setEditingRing(null) }}
                      autoFocus
                      className="px-2 py-0.5 bg-surface border border-border rounded text-sm w-32" />
                    <button onClick={() => renameRing(r.id)} disabled={busy}
                      className="text-success cursor-pointer bg-transparent border-none p-1"><Check className="w-3.5 h-3.5" /></button>
                    <button onClick={() => setEditingRing(null)}
                      className="text-text-muted cursor-pointer bg-transparent border-none p-1"><X className="w-3.5 h-3.5" /></button>
                  </>
                ) : (
                  <>
                    <span className="text-sm text-primary font-medium px-1">{r.name}</span>
                    <button onClick={() => { setEditingRing(r.id); setEditRingName(r.name) }}
                      className="text-text-muted hover:text-text cursor-pointer bg-transparent border-none p-1" title="Переименовать"><Pencil className="w-3.5 h-3.5" /></button>
                    <button onClick={() => deleteRing(r.id)} disabled={busy}
                      className="text-danger cursor-pointer bg-transparent border-none p-1" title="Удалить"><Trash2 className="w-3.5 h-3.5" /></button>
                  </>
                )}
                <button onClick={() => moveRingPos(r.id, 1)} disabled={busy || i === rings.length - 1}
                  className="text-text-muted hover:text-text disabled:opacity-30 cursor-pointer bg-transparent border-none px-1" title="Вправо">›</button>
              </div>
            ))}
          </div>
        )}
        <div className="flex gap-2">
          <input value={newRingName} onChange={(e) => setNewRingName(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') addRing() }}
            placeholder="Название нового ринга, например «Ринг А»"
            className="flex-1 px-3 py-2 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary/40" />
          <button onClick={addRing} disabled={busy || !newRingName.trim()}
            className="flex items-center gap-1.5 px-4 py-2 bg-primary hover:bg-primary-dark text-white rounded-lg text-sm cursor-pointer border-none disabled:opacity-50 font-medium">
            <Plus className="w-4 h-4" /> Добавить ринг
          </button>
        </div>
      </div>

      {rings.length === 0 ? (
        <div className="bg-surface-light rounded-xl border border-dashed border-border p-10 text-center">
          <Plus className="w-10 h-10 text-text-muted mx-auto mb-3" />
          <p className="text-text font-medium mb-1">Сначала добавьте хотя бы один ринг</p>
          <p className="text-text-muted text-sm">Без рингов некуда распределять бои.</p>
        </div>
      ) : (
        <div className="grid lg:grid-cols-[340px_1fr] gap-6">
          {/* Pool of unscheduled pairs */}
          <div className="bg-surface-light rounded-xl border border-border p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
                Нераспределённые пары
              </h3>
              <span className="text-xs px-2 py-0.5 rounded-full bg-accent/15 text-accent font-semibold">{filtered.length}</span>
            </div>
            <p className="text-xs text-text-muted mb-3">Перетащите карточку в нужный день и ринг справа.</p>
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
            <div className="space-y-3 max-h-[65vh] overflow-y-auto pr-1">
              {filtered.length === 0 && (
                <div className="text-center py-8">
                  <Check className="w-8 h-8 text-success mx-auto mb-2" />
                  <p className="text-text-muted text-sm">Все пары распределены</p>
                </div>
              )}
              {groupedPairs.map((group) => (
                <PoolGroup
                  key={group.key}
                  group={group}
                  isOpen={openGroups[group.key] !== false}
                  onToggle={() => setOpenGroups({ ...openGroups, [group.key]: openGroups[group.key] === false })}
                  onDragStart={(p) => setDrag({ type: 'pair', pair: p })}
                  onDragEnd={() => setDrag(null)}
                />
              ))}
            </div>
          </div>

          {/* Schedule grid */}
          <div className="overflow-x-auto">
            {selectedFights.size > 0 && (
              <div className="bg-accent/10 border border-accent/30 rounded-lg px-3 py-2 mb-3 text-sm flex items-center justify-between">
                <span className="text-accent font-medium">Выбрано: {selectedFights.size}. Перетащите или нажмите «Перенести сюда» в нужной ячейке.</span>
                <button onClick={() => setSelectedFights(new Set())} className="text-text-muted hover:text-text cursor-pointer bg-transparent border-none text-xs">Снять выделение</button>
              </div>
            )}
            <div className="rounded-xl border border-border overflow-hidden">
              <table className="w-full border-collapse bg-surface-light">
                <thead className="bg-surface">
                  <tr>
                    <th className="text-left px-3 py-2.5 text-xs text-text-muted font-semibold uppercase tracking-wide border-b border-border w-28">Ринг</th>
                    {effectiveDays.map((d) => (
                      <th key={d.day_number} className="text-left px-3 py-2.5 text-xs text-text-muted font-semibold uppercase tracking-wide border-b border-l border-border min-w-[280px]">
                        День {d.day_number}{d.date ? <span className="text-text/70 normal-case font-normal ml-1">/ {formatDateShort(d.date)}</span> : ''}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rings.map((r) => (
                    <tr key={r.id}>
                      <td className="align-top px-3 py-3 text-sm font-semibold text-primary border-b border-border bg-surface/40">{r.name}</td>
                      {effectiveDays.map((d) => {
                        const cellFights = fights
                          .filter((f) => f.ring_id === r.id && f.day_number === d.day_number)
                          .sort((a, b) => a.fight_order - b.fight_order)
                        const isEmpty = cellFights.length === 0
                        return (
                          <td key={d.day_number}
                            onDragOver={(e) => e.preventDefault()}
                            onDrop={(e) => { e.preventDefault(); dropOnCell(r.id, d.day_number) }}
                            className={`align-top p-2 border-b border-l border-border transition-colors ${drag ? 'bg-primary/5' : ''}`}>
                            <div className="space-y-2 min-h-[80px]">
                              {isEmpty && (
                                <div className="border-2 border-dashed border-border rounded-lg p-4 text-center text-text-muted text-xs">
                                  Перетащите пару сюда
                                </div>
                              )}
                              {cellFights.map((f, idx) => {
                                const sel = selectedFights.has(f.id)
                                const classBadge = f.class_name?.trim().charAt(0) || '?'
                                return (
                                  <div key={f.id} draggable
                                    onDragStart={() => setDrag({ type: 'fight', fightId: f.id })}
                                    onDragEnd={() => setDrag(null)}
                                    className={`group rounded-lg border transition-colors cursor-grab active:cursor-grabbing ${
                                      sel ? 'bg-accent/15 border-accent/60' : 'bg-surface border-border hover:border-primary/40 hover:shadow-sm'
                                    }`}>
                                    <div className="flex items-center gap-1.5 px-2 py-1.5 border-b border-border/50">
                                      <input type="checkbox" checked={sel} onChange={() => toggleSelect(f.id)}
                                        className="cursor-pointer" onClick={(e) => e.stopPropagation()} />
                                      <GripVertical className="w-3.5 h-3.5 text-text-muted" />
                                      <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-primary/15 text-primary text-xs font-bold">№{idx + 1}</span>
                                      <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-primary/10 text-primary text-[10px] font-semibold" title={f.class_name}>{classBadge}</span>
                                      <span className="text-[11px] text-text-muted truncate flex-1">{f.gender === 'Мужской' ? 'М' : 'Ж'} · {f.age_category_name} · {f.weight_name} кг</span>
                                      {f.round_label && <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent">{f.round_label}</span>}
                                      <div className="flex items-center opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button onClick={() => moveFightInCell(r.id, d.day_number, f.id, -1)} disabled={busy || idx === 0}
                                          className="text-text-muted hover:text-text disabled:opacity-30 cursor-pointer bg-transparent border-none px-1" title="Выше">↑</button>
                                        <button onClick={() => moveFightInCell(r.id, d.day_number, f.id, 1)} disabled={busy || idx === cellFights.length - 1}
                                          className="text-text-muted hover:text-text disabled:opacity-30 cursor-pointer bg-transparent border-none px-1" title="Ниже">↓</button>
                                        <button onClick={() => removeFight(f.id)} disabled={busy}
                                          className="text-danger cursor-pointer bg-transparent border-none p-0.5 ml-1" title="Удалить">
                                          <Trash2 className="w-3.5 h-3.5" />
                                        </button>
                                      </div>
                                    </div>
                                    <div className="px-2 py-1.5 text-xs space-y-0.5">
                                      <div className="text-text font-medium truncate">{f.fighter1?.fio ?? '—'}</div>
                                      <div className="text-[10px] text-text-muted truncate">{f.fighter1?.club_name ?? ''}</div>
                                      <div className="text-text-muted text-center text-[10px] font-bold py-0.5">vs</div>
                                      <div className="text-text font-medium truncate">{f.fighter2?.fio ?? '—'}</div>
                                      <div className="text-[10px] text-text-muted truncate">{f.fighter2?.club_name ?? ''}</div>
                                    </div>
                                  </div>
                                )
                              })}
                              <div className="flex items-center gap-3 pt-1 flex-wrap">
                                {cellFights.length > 0 && d.day_number < (effectiveDays[effectiveDays.length - 1]?.day_number ?? 1) + 1 && (
                                  <button onClick={() => moveRingToNextDay(r.id, d.day_number)} disabled={busy}
                                    className="text-xs text-text-muted hover:text-primary cursor-pointer bg-transparent border-none flex items-center gap-1">
                                    <ArrowRight className="w-3 h-3" /> На следующий день
                                  </button>
                                )}
                                {selectedFights.size > 0 && (
                                  <button onClick={() => bulkMove(r.id, d.day_number)} disabled={busy}
                                    className="text-xs text-accent font-medium hover:underline cursor-pointer bg-transparent border-none">
                                    ← Перенести выбранное сюда
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

function PoolGroup({
  group, isOpen, onToggle, onDragStart, onDragEnd,
}: {
  group: { key: string; title: string; subtitle: string; items: Pair[] }
  isOpen: boolean
  onToggle: () => void
  onDragStart: (p: Pair) => void
  onDragEnd: () => void
}) {
  return (
    <div className="border border-border rounded-lg overflow-hidden bg-surface/40">
      <button onClick={onToggle}
        className="w-full flex items-center gap-2 px-2.5 py-2 text-left bg-transparent border-none cursor-pointer hover:bg-surface transition-colors">
        {isOpen ? <ChevronDown className="w-3.5 h-3.5 text-text-muted shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-text-muted shrink-0" />}
        <div className="flex-1 min-w-0">
          <div className="text-xs text-text font-semibold truncate">{group.title}</div>
          <div className="text-[10px] text-text-muted">{group.subtitle}</div>
        </div>
        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-accent/15 text-accent font-semibold">{group.items.length}</span>
      </button>
      {isOpen && (
        <div className="p-2 space-y-1.5 border-t border-border/50">
          {group.items.map((p) => (
            <div key={p.pair_key} draggable
              onDragStart={() => onDragStart(p)}
              onDragEnd={onDragEnd}
              className="bg-surface border border-border rounded-md p-2 cursor-grab active:cursor-grabbing hover:border-primary/40 transition-colors">
              <div className="flex items-center gap-1.5 mb-1">
                <GripVertical className="w-3 h-3 text-text-muted" />
                {p.round_label && <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent">{p.round_label}</span>}
              </div>
              <div className="text-xs text-text">
                <div className="font-medium truncate">{shortFighter(p.fighter1)}</div>
                <div className="text-text-muted text-[10px] text-center py-0.5">vs</div>
                <div className="font-medium truncate">{shortFighter(p.fighter2)}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

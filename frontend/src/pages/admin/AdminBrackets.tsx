import { useEffect, useState, useCallback } from 'react'
import { adminApi, competitionsApi } from '../../api'
import { Trophy, Check, X, RefreshCw, ChevronLeft, Loader2, Download } from 'lucide-react'

interface Competition {
  id: number
  name: string
  discipline: string
}

interface Category {
  class_name: string
  gender: string
  age_category_name: string
  weight_name: string
  participant_count: number
  approved: boolean
}

interface BracketParticipant {
  id?: number
  fio: string
  club_name: string
  city_name: string
  class_name: string
}

export default function AdminBrackets() {
  const [competitions, setCompetitions] = useState<Competition[]>([])
  const [competitionId, setCompetitionId] = useState<number | undefined>(undefined)
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<Category | null>(null)
  const [bracket, setBracket] = useState<(BracketParticipant | null)[]>([])
  const [isApproved, setIsApproved] = useState(false)
  const [swapFrom, setSwapFrom] = useState<number | null>(null)
  const [actionLoading, setActionLoading] = useState(false)
  const [bracketImageUrl, setBracketImageUrl] = useState('')

  useEffect(() => {
    competitionsApi.getAll().then((r) => {
      const list: Competition[] = r.data
      setCompetitions(list)
      if (list.length === 1) setCompetitionId(list[0].id)
    })
  }, [])

  useEffect(() => {
    loadCategories(competitionId)
  }, [competitionId])

  const loadCategories = (cid?: number) => {
    setLoading(true)
    setSelected(null)
    adminApi.getBracketCategories(cid).then((r) => {
      setCategories(r.data)
      setLoading(false)
    })
  }

  const buildParams = (cat: Category) => ({
    class_name: cat.class_name,
    gender: cat.gender,
    age_category_name: cat.age_category_name,
    weight_name: cat.weight_name,
    ...(competitionId !== undefined ? { competition_id: competitionId } : {}),
  })

  const selectCategory = useCallback(async (cat: Category) => {
    setSelected(cat)
    setSwapFrom(null)
    setActionLoading(true)
    try {
      const params = {
        class_name: cat.class_name,
        gender: cat.gender,
        age_category_name: cat.age_category_name,
        weight_name: cat.weight_name,
        ...(competitionId !== undefined ? { competition_id: competitionId } : {}),
      }
      const res = await adminApi.getBracketDetail(params)
      setBracket(res.data.participants)
      setIsApproved(res.data.approved)
      try {
        const blobUrl = await adminApi.fetchBracketImageBlob(params)
        setBracketImageUrl(blobUrl)
      } catch {
        setBracketImageUrl('')
      }
    } catch {}
    setActionLoading(false)
  }, [competitionId])

  const handleSwap = async (index: number) => {
    if (!selected) return
    if (swapFrom === null) {
      setSwapFrom(index)
      return
    }
    if (swapFrom === index) {
      setSwapFrom(null)
      return
    }
    setActionLoading(true)
    try {
      await adminApi.swapParticipants({
        ...buildParams(selected),
        index_a: swapFrom,
        index_b: index,
      })
      setSwapFrom(null)
      await selectCategory(selected)
    } catch {}
    setActionLoading(false)
  }

  const handleToggleApproval = async () => {
    if (!selected) return
    setActionLoading(true)
    try {
      const res = await adminApi.toggleApproval(buildParams(selected))
      setIsApproved(res.data.approved)
      loadCategories(competitionId)
    } catch {}
    setActionLoading(false)
  }

  const handleRegenerate = async () => {
    if (!selected) return
    setActionLoading(true)
    try {
      await adminApi.regenerateBracket(buildParams(selected))
      await selectCategory(selected)
    } catch {}
    setActionLoading(false)
  }

  if (selected) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <button onClick={() => setSelected(null)} className="flex items-center gap-2 text-text-muted hover:text-text mb-4 cursor-pointer bg-transparent border-none text-sm">
          <ChevronLeft className="w-4 h-4" /> Назад к списку
        </button>

        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold">
              {selected.class_name} - {selected.gender}
            </h1>
            <p className="text-text-secondary text-sm">{selected.age_category_name}, {selected.weight_name} kg</p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${isApproved ? 'bg-success/10 text-success' : 'bg-surface-lighter text-text-muted'}`}>
              {isApproved ? 'Утверждено' : 'Не утверждено'}
            </span>
          </div>
        </div>

        <div className="grid lg:grid-cols-[300px_1fr] gap-6">
          <div className="space-y-4">
            <div className="bg-surface-light rounded-xl border border-border p-4">
              <h3 className="text-sm font-semibold text-text-secondary mb-3">Участники (нажмите для swap)</h3>
              <div className="space-y-1">
                {bracket.map((p, i) => (
                  <button
                    key={i}
                    onClick={() => p && handleSwap(i)}
                    disabled={!p || actionLoading}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm cursor-pointer border transition-all ${
                      !p ? 'bg-surface-lighter/30 text-text-muted border-transparent cursor-default' :
                      swapFrom === i ? 'bg-accent/10 border-accent/50 text-accent' :
                      'bg-surface border-border hover:border-primary/30 text-text'
                    }`}
                  >
                    {p ? (
                      <div>
                        <div className="font-medium">{p.fio}</div>
                        <div className="text-xs text-text-muted">{p.club_name}</div>
                      </div>
                    ) : (
                      <span className="text-text-muted italic">BYE</span>
                    )}
                  </button>
                ))}
              </div>
              {swapFrom !== null && (
                <button onClick={() => setSwapFrom(null)} className="mt-2 w-full py-2 bg-surface border border-border rounded-lg text-text-muted text-xs cursor-pointer">
                  Сбросить выбор
                </button>
              )}
            </div>

            <div className="flex flex-col gap-2">
              <button onClick={handleRegenerate} disabled={actionLoading}
                className="flex items-center justify-center gap-2 py-2.5 bg-surface-light border border-border rounded-lg text-text-secondary text-sm font-medium cursor-pointer hover:border-primary/30 transition-colors disabled:opacity-50">
                <RefreshCw className="w-4 h-4" /> Перегенерировать
              </button>
              <button onClick={handleToggleApproval} disabled={actionLoading}
                className={`flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium cursor-pointer border-none transition-colors disabled:opacity-50 ${
                  isApproved ? 'bg-danger/10 text-danger hover:bg-danger/20' : 'bg-success/10 text-success hover:bg-success/20'
                }`}>
                {isApproved ? <><X className="w-4 h-4" /> Снять утверждение</> : <><Check className="w-4 h-4" /> Утвердить</>}
              </button>
              <button
                onClick={() => {
                  adminApi.downloadBracketPng(buildParams(selected)).catch(() => {})
                }}
                disabled={actionLoading}
                className="flex items-center justify-center gap-2 py-2.5 bg-surface-light border border-border rounded-lg text-text-secondary text-sm font-medium cursor-pointer hover:border-success/30 transition-colors disabled:opacity-50"
              >
                <Download className="w-4 h-4" /> Скачать PNG
              </button>
            </div>
          </div>

          <div className="bg-surface-light rounded-xl border border-border p-4 overflow-x-auto">
            {actionLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-text-muted" />
              </div>
            ) : (
              <img src={bracketImageUrl} alt="Турнирная сетка" className="max-w-full" />
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Управление сетками</h1>
        {competitions.length > 1 && (
          <select
            value={competitionId ?? ''}
            onChange={(e) => setCompetitionId(e.target.value ? Number(e.target.value) : undefined)}
            className="px-3 py-2 bg-surface-light border border-border rounded-lg text-sm text-text focus:outline-none focus:border-primary/50"
          >
            <option value="">Все соревнования</option>
            {competitions.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        )}
      </div>

      {loading ? (
        <div className="text-center py-12 text-text-muted">Загрузка...</div>
      ) : categories.length === 0 ? (
        <div className="text-center py-16">
          <Trophy className="w-16 h-16 mx-auto mb-4 text-text-muted" />
          <p className="text-text-muted text-lg">Нет категорий с участниками</p>
        </div>
      ) : (
        <div className="bg-surface-light rounded-xl border border-border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="px-4 py-3 text-text-muted font-medium">#</th>
                <th className="px-4 py-3 text-text-muted font-medium">Класс</th>
                <th className="px-4 py-3 text-text-muted font-medium">Пол</th>
                <th className="px-4 py-3 text-text-muted font-medium">Возраст</th>
                <th className="px-4 py-3 text-text-muted font-medium">Вес</th>
                <th className="px-4 py-3 text-text-muted font-medium">Участников</th>
                <th className="px-4 py-3 text-text-muted font-medium">Статус</th>
              </tr>
            </thead>
            <tbody>
              {categories.map((c, i) => (
                <tr key={i} onClick={() => selectCategory(c)}
                  className="border-b border-border/50 hover:bg-surface-lighter/30 transition-colors cursor-pointer">
                  <td className="px-4 py-3 text-text-muted">{i + 1}</td>
                  <td className="px-4 py-3 font-medium">{c.class_name}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-1 rounded-full ${c.gender === 'Мужской' ? 'bg-male/10 text-male' : 'bg-female/10 text-female'}`}>
                      {c.gender === 'Мужской' ? 'М' : 'Ж'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-text-secondary">{c.age_category_name}</td>
                  <td className="px-4 py-3 text-text-secondary">{c.weight_name}</td>
                  <td className="px-4 py-3 text-text-secondary">{c.participant_count}</td>
                  <td className="px-4 py-3">
                    {c.approved ? (
                      <span className="flex items-center gap-1 text-success text-xs"><Check className="w-3 h-3" /> Утверждено</span>
                    ) : (
                      <span className="text-text-muted text-xs">Не утверждено</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

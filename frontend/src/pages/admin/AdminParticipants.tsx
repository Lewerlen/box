import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { adminApi, publicApi, competitionsApi } from '../../api'
import { Search, ChevronLeft, ChevronRight, Trash2, Edit3, Upload, X, Loader2 } from 'lucide-react'

interface Participant {
  id: number
  fio: string
  gender: string
  dob: string
  age_category_name: string
  weight: string
  class_name: string
  region_name: string
  city_name: string
  club_name: string
  coach_name: string
  rank_title: string
}

interface RefItem {
  id: number
  name: string
  gender?: string
}

interface Competition {
  id: number
  name: string
}

interface EditData {
  fio?: string
  gender?: string
  dob?: string
  class_name?: string
  rank_name?: string
  region_name?: string
  city_name?: string
  club_name?: string
  coach_name?: string
}

export default function AdminParticipants() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [participants, setParticipants] = useState<Participant[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [search, setSearch] = useState('')
  const [competitionId, setCompetitionId] = useState<string>(searchParams.get('competition_id') || '')
  const [competitions, setCompetitions] = useState<Competition[]>([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editData, setEditData] = useState<EditData>({})
  const [saving, setSaving] = useState(false)
  const [csvUploading, setCsvUploading] = useState(false)
  const [csvResult, setCsvResult] = useState<{ created?: number; updated?: number; errors: number; error_details?: string[] } | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)
  const [classes, setClasses] = useState<RefItem[]>([])
  const [ranks, setRanks] = useState<RefItem[]>([])

  useEffect(() => {
    publicApi.getClasses().then((r) => setClasses(r.data))
    publicApi.getRanks().then((r) => setRanks(r.data))
    competitionsApi.getAll().then((r) => setCompetitions(r.data))
  }, [])

  useEffect(() => {
    setCompetitionId(searchParams.get('competition_id') || '')
    setPage(1)
  }, [searchParams])

  const load = useCallback(() => {
    setLoading(true)
    const params: { page: number; search?: string; competition_id?: number } = { page }
    if (search) params.search = search
    if (competitionId) params.competition_id = Number(competitionId)
    adminApi.getParticipants(params).then((r) => {
      setParticipants(r.data.participants)
      setTotal(r.data.total)
      setTotalPages(r.data.total_pages)
      setLoading(false)
    })
  }, [page, search, competitionId])

  useEffect(() => { load() }, [load])

  const handleCompetitionChange = (value: string) => {
    setCompetitionId(value)
    setPage(1)
    if (value) {
      setSearchParams({ competition_id: value })
    } else {
      setSearchParams({})
    }
  }

  const handleEdit = (p: Participant) => {
    setEditingId(p.id)
    setEditData({
      fio: p.fio,
      gender: p.gender,
      dob: p.dob || '',
      class_name: p.class_name || '',
      rank_name: p.rank_title || '',
      region_name: p.region_name || '',
      city_name: p.city_name || '',
      club_name: p.club_name || '',
      coach_name: p.coach_name || '',
    })
  }

  const handleSave = async () => {
    if (!editingId) return
    setSaving(true)
    try {
      await adminApi.updateParticipant(editingId, editData)
      setEditingId(null)
      load()
    } catch { }
    setSaving(false)
  }

  const handleDelete = async (id: number) => {
    try {
      await adminApi.deleteParticipant(id)
      setDeleteConfirm(null)
      load()
    } catch { }
  }

  const handleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setCsvUploading(true)
    setCsvResult(null)
    try {
      const res = await adminApi.importCsv(file)
      setCsvResult(res.data)
      load()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setCsvResult({ errors: -1, error_details: [err.response?.data?.detail || 'Ошибка'] })
    }
    setCsvUploading(false)
    e.target.value = ''
  }

  const handleDownloadExcel = () => {
    adminApi.downloadExcel('preliminary', competitionId ? Number(competitionId) : undefined)
  }

  const inputCls = "w-full px-3 py-2 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none"

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Управление участниками</h1>
          <p className="text-text-muted text-sm mt-1">Всего: {total}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownloadExcel}
            className="flex items-center gap-2 px-4 py-2 bg-surface-light border border-border text-text-secondary rounded-lg text-sm font-medium cursor-pointer hover:bg-surface-lighter transition-colors"
          >
            Скачать Excel
          </button>
          <label className="flex items-center gap-2 px-4 py-2 bg-accent/10 border border-accent/30 text-accent rounded-lg text-sm font-medium cursor-pointer hover:bg-accent/20 transition-colors">
            <Upload className="w-4 h-4" />
            {csvUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Импорт CSV'}
            <input type="file" accept=".csv" onChange={handleCsvUpload} className="hidden" />
          </label>
        </div>
      </div>

      {csvResult && (
        <div className={`rounded-lg px-4 py-3 mb-4 text-sm ${csvResult.errors === -1 ? 'bg-danger/10 border border-danger/30 text-danger' : 'bg-success/10 border border-success/30 text-success'}`}>
          {csvResult.errors === -1 ? (
            <p>{csvResult.error_details?.join(', ')}</p>
          ) : (
            <p>Создано: {csvResult.created}, Обновлено: {csvResult.updated}, Ошибок: {csvResult.errors}
              {(csvResult.error_details?.length ?? 0) > 0 && ` (${csvResult.error_details?.join('; ')})`}
            </p>
          )}
          <button onClick={() => setCsvResult(null)} className="text-xs underline mt-1 bg-transparent border-none cursor-pointer text-inherit">Закрыть</button>
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <div className="sm:w-72">
          <select
            value={competitionId}
            onChange={(e) => handleCompetitionChange(e.target.value)}
            className="w-full px-3 py-3 bg-surface-light border border-border rounded-xl text-text focus:outline-none focus:border-primary/50 transition-colors text-sm"
          >
            <option value="">Все соревнования</option>
            {competitions.map((c) => (
              <option key={c.id} value={String(c.id)}>{c.name}</option>
            ))}
          </select>
        </div>
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
          <input
            type="text" placeholder="Поиск по ФИО..." value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            className="w-full pl-10 pr-4 py-3 bg-surface-light border border-border rounded-xl text-text placeholder:text-text-muted focus:outline-none focus:border-primary/50 transition-colors"
          />
        </div>
      </div>

      {editingId && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
          <div className="bg-surface-light rounded-xl border border-border p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Редактирование</h3>
              <button onClick={() => setEditingId(null)} className="text-text-muted hover:text-text cursor-pointer bg-transparent border-none"><X className="w-5 h-5" /></button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="sm:col-span-2">
                <label className="block text-sm text-text-secondary mb-1">ФИО</label>
                <input value={editData.fio || ''} onChange={(e) => setEditData({ ...editData, fio: e.target.value })} className={inputCls} />
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">Пол</label>
                <select value={editData.gender || ''} onChange={(e) => setEditData({ ...editData, gender: e.target.value })} className={inputCls}>
                  <option value="Мужской">Мужской</option>
                  <option value="Женский">Женский</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">Дата рождения</label>
                <input type="date" value={editData.dob || ''} onChange={(e) => setEditData({ ...editData, dob: e.target.value })} className={inputCls} />
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">Класс</label>
                <select value={editData.class_name || ''} onChange={(e) => setEditData({ ...editData, class_name: e.target.value })} className={inputCls}>
                  <option value="">—</option>
                  {classes.map((c) => (
                    <option key={c.id} value={c.name}>{c.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">Разряд</label>
                <select value={editData.rank_name || ''} onChange={(e) => setEditData({ ...editData, rank_name: e.target.value })} className={inputCls}>
                  <option value="">—</option>
                  {ranks.map((r) => (
                    <option key={r.id} value={r.name}>{r.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">Регион</label>
                <input value={editData.region_name || ''} onChange={(e) => setEditData({ ...editData, region_name: e.target.value })} className={inputCls} />
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">Город</label>
                <input value={editData.city_name || ''} onChange={(e) => setEditData({ ...editData, city_name: e.target.value })} className={inputCls} />
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">Клуб</label>
                <input value={editData.club_name || ''} onChange={(e) => setEditData({ ...editData, club_name: e.target.value })} className={inputCls} />
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">Тренер</label>
                <input value={editData.coach_name || ''} onChange={(e) => setEditData({ ...editData, coach_name: e.target.value })} className={inputCls} />
              </div>
            </div>
            <div className="flex gap-3 mt-4">
              <button onClick={() => setEditingId(null)} className="flex-1 py-2 bg-surface border border-border rounded-lg text-text-secondary cursor-pointer">Отмена</button>
              <button onClick={handleSave} disabled={saving} className="flex-1 py-2 bg-primary text-white rounded-lg font-medium cursor-pointer border-none disabled:opacity-50">
                {saving ? 'Сохранение...' : 'Сохранить'}
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
          <div className="bg-surface-light rounded-xl border border-border p-6 w-full max-w-sm text-center">
            <Trash2 className="w-12 h-12 text-danger mx-auto mb-3" />
            <h3 className="text-lg font-semibold mb-2">Удалить участника?</h3>
            <p className="text-text-muted text-sm mb-4">Это действие нельзя отменить</p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteConfirm(null)} className="flex-1 py-2 bg-surface border border-border rounded-lg text-text-secondary cursor-pointer">Отмена</button>
              <button onClick={() => handleDelete(deleteConfirm)} className="flex-1 py-2 bg-danger text-white rounded-lg font-medium cursor-pointer border-none">Удалить</button>
            </div>
          </div>
        </div>
      )}

      <div className="bg-surface-light rounded-xl border border-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="px-4 py-3 text-text-muted font-medium">ID</th>
                <th className="px-4 py-3 text-text-muted font-medium">ФИО</th>
                <th className="px-4 py-3 text-text-muted font-medium hidden sm:table-cell">Пол</th>
                <th className="px-4 py-3 text-text-muted font-medium hidden md:table-cell">Возраст</th>
                <th className="px-4 py-3 text-text-muted font-medium">Вес</th>
                <th className="px-4 py-3 text-text-muted font-medium hidden lg:table-cell">Класс</th>
                <th className="px-4 py-3 text-text-muted font-medium hidden lg:table-cell">Клуб</th>
                <th className="px-4 py-3 text-text-muted font-medium w-24">Действия</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={8} className="px-4 py-12 text-center text-text-muted">Загрузка...</td></tr>
              ) : participants.length === 0 ? (
                <tr><td colSpan={8} className="px-4 py-12 text-center text-text-muted">Участники не найдены</td></tr>
              ) : (
                participants.map((p) => (
                  <tr key={p.id} className="border-b border-border/50 hover:bg-surface-lighter/30 transition-colors">
                    <td className="px-4 py-3 text-text-muted">{p.id}</td>
                    <td className="px-4 py-3 font-medium">{p.fio}</td>
                    <td className="px-4 py-3 hidden sm:table-cell">
                      <span className={`text-xs px-2 py-1 rounded-full ${p.gender === 'Мужской' ? 'bg-male/10 text-male' : 'bg-female/10 text-female'}`}>
                        {p.gender === 'Мужской' ? 'М' : 'Ж'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-text-secondary hidden md:table-cell">{p.age_category_name}</td>
                    <td className="px-4 py-3 text-text-secondary">{p.weight}</td>
                    <td className="px-4 py-3 text-text-secondary hidden lg:table-cell">{p.class_name}</td>
                    <td className="px-4 py-3 text-text-secondary hidden lg:table-cell">{p.club_name}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button onClick={() => handleEdit(p)} className="p-1.5 rounded hover:bg-surface-lighter text-text-muted hover:text-accent cursor-pointer bg-transparent border-none transition-colors">
                          <Edit3 className="w-4 h-4" />
                        </button>
                        <button onClick={() => setDeleteConfirm(p.id)} className="p-1.5 rounded hover:bg-surface-lighter text-text-muted hover:text-danger cursor-pointer bg-transparent border-none transition-colors">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page <= 1}
            className="p-2 rounded-lg bg-surface-light border border-border disabled:opacity-30 cursor-pointer disabled:cursor-default text-text">
            <ChevronLeft className="w-5 h-5" />
          </button>
          <span className="px-4 py-2 text-sm text-text-secondary">{page} / {totalPages}</span>
          <button onClick={() => setPage(Math.min(totalPages, page + 1))} disabled={page >= totalPages}
            className="p-2 rounded-lg bg-surface-light border border-border disabled:opacity-30 cursor-pointer disabled:cursor-default text-text">
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      )}
    </div>
  )
}

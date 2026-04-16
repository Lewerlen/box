import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { adminApi, publicApi, competitionsApi } from '../../api'
import {
  ChevronLeft, Pencil, Check, X, Loader2, Download, FileSpreadsheet,
  Users, Trophy, Upload, Search, ChevronRight, Trash2, Edit3,
  RefreshCw, Lock, Unlock, CalendarDays
} from 'lucide-react'
import AdminSchedule from './AdminSchedule'

interface Competition {
  id: number
  name: string
  discipline: string
  date_start: string | null
  date_end: string | null
  location: string | null
  status: string
  registration_deadline: string | null
  registration_open_at: string | null
  registration_closed: boolean
}

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
  competition_id: number | null
  competition_name: string | null
}

interface RefItem {
  id: number
  name: string
  gender?: string
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

const DISCIPLINE_LABEL: Record<string, string> = {
  muay_thai: 'Тайский бокс',
  kickboxing: 'Кикбоксинг',
}

const DISCIPLINE_OPTIONS = [
  { value: 'muay_thai', label: 'Тайский бокс' },
  { value: 'kickboxing', label: 'Кикбоксинг' },
]

const DISCIPLINE_COLORS: Record<string, string> = {
  muay_thai: 'bg-red-500/15 text-red-400 border border-red-500/30',
  kickboxing: 'bg-blue-500/15 text-blue-400 border border-blue-500/30',
}

const STATUS_OPTIONS = [
  { value: 'upcoming', label: 'Скоро' },
  { value: 'active', label: 'Идёт регистрация' },
  { value: 'finished', label: 'Завершено' },
]

const STATUS_LABEL: Record<string, string> = {
  active: 'Идёт регистрация',
  upcoming: 'Скоро',
  finished: 'Завершено',
}

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-500/15 text-green-400',
  upcoming: 'bg-yellow-500/15 text-yellow-400',
  finished: 'bg-gray-500/15 text-gray-400',
}

function toDateTimeLocal(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  const local = new Date(d.getTime() - d.getTimezoneOffset() * 60000)
  return local.toISOString().slice(0, 16)
}

function fromDateTimeLocal(str: string): string | null {
  if (!str) return null
  return new Date(str).toISOString()
}

function isEventPast(dateEnd: string | null | undefined): boolean {
  if (!dateEnd) return false
  const end = new Date(dateEnd)
  end.setHours(23, 59, 59, 999)
  return end < new Date()
}

const emptyForm = {
  name: '',
  discipline: 'muay_thai',
  date_start: '',
  date_end: '',
  location: '',
  status: 'upcoming',
  registration_deadline: '',
  registration_open_at: '',
  registration_closed: false,
}

type Tab = 'participants' | 'brackets' | 'schedule'

export default function AdminCompetitionDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const competitionId = Number(id)

  const [competition, setCompetition] = useState<Competition | null>(null)
  const [loadingComp, setLoadingComp] = useState(true)
  const [showEditForm, setShowEditForm] = useState(false)
  const [form, setForm] = useState({ ...emptyForm })
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')
  const [activeTab, setActiveTab] = useState<Tab>('participants')
  const [downloading, setDownloading] = useState('')

  const loadCompetition = useCallback(() => {
    setLoadingComp(true)
    competitionsApi.getById(competitionId)
      .then((r) => setCompetition(r.data))
      .catch(() => navigate('/admin/competitions'))
      .finally(() => setLoadingComp(false))
  }, [competitionId, navigate])

  useEffect(() => { loadCompetition() }, [loadCompetition])

  const openEdit = () => {
    if (!competition) return
    setForm({
      name: competition.name,
      discipline: competition.discipline,
      date_start: competition.date_start ?? '',
      date_end: competition.date_end ?? '',
      location: competition.location ?? '',
      status: competition.status,
      registration_deadline: toDateTimeLocal(competition.registration_deadline),
      registration_open_at: toDateTimeLocal(competition.registration_open_at),
      registration_closed: competition.registration_closed,
    })
    setFormError('')
    setShowEditForm(true)
  }

  const handleSave = async () => {
    if (!form.name.trim()) { setFormError('Введите название соревнования'); return }
    setSaving(true)
    setFormError('')
    try {
      await competitionsApi.update(competitionId, {
        name: form.name.trim(),
        discipline: form.discipline,
        date_start: form.date_start || undefined,
        date_end: form.date_end || undefined,
        location: form.location.trim() || undefined,
        status: form.status,
        registration_deadline: fromDateTimeLocal(form.registration_deadline),
        registration_open_at: fromDateTimeLocal(form.registration_open_at),
        registration_closed: form.registration_closed,
      })
      setShowEditForm(false)
      loadCompetition()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setFormError(err.response?.data?.detail ?? 'Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  const handleDownload = async (type: 'preliminary' | 'weigh-in' | 'brackets' | 'protocol') => {
    setDownloading(type)
    try { await adminApi.downloadExcel(type, competitionId) } catch {}
    setDownloading('')
  }

  const toggleRegClosed = async () => {
    if (!competition) return
    try {
      await competitionsApi.update(competitionId, { registration_closed: !competition.registration_closed })
      loadCompetition()
    } catch {}
  }

  if (loadingComp) return <div className="text-center py-12 text-text-muted">Загрузка...</div>
  if (!competition) return null

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center gap-2 mb-6 text-sm text-text-muted">
        <Link to="/admin/competitions" className="hover:text-text transition-colors flex items-center gap-1">
          <ChevronLeft className="w-4 h-4" /> Соревнования
        </Link>
        <span>/</span>
        <span className="text-text truncate max-w-xs">{competition.name}</span>
      </div>

      <div className="bg-surface-light rounded-xl border border-border p-5 mb-6">
        {showEditForm ? (
          <div>
            <h2 className="text-lg font-semibold mb-4 text-text">Редактировать соревнование</h2>
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="sm:col-span-2">
                <label className="block text-sm text-text-muted mb-1">Название *</label>
                <input
                  type="text" value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Чемпионат Республики..."
                  className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary"
                />
              </div>
              <div>
                <label className="block text-sm text-text-muted mb-1">Дисциплина</label>
                <select value={form.discipline} onChange={(e) => setForm({ ...form, discipline: e.target.value })}
                  className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary">
                  {DISCIPLINE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm text-text-muted mb-1">Статус</label>
                <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}
                  className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary">
                  {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm text-text-muted mb-1">Дата начала</label>
                <input type="date" value={form.date_start} onChange={(e) => setForm({ ...form, date_start: e.target.value })}
                  className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary" />
              </div>
              <div>
                <label className="block text-sm text-text-muted mb-1">Дата окончания</label>
                <input type="date" value={form.date_end} onChange={(e) => setForm({ ...form, date_end: e.target.value })}
                  className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary" />
              </div>
              <div>
                <label className="block text-sm text-text-muted mb-1">Открытие регистрации</label>
                <input type="datetime-local" value={form.registration_open_at} onChange={(e) => setForm({ ...form, registration_open_at: e.target.value })}
                  className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary" />
              </div>
              <div>
                <label className="block text-sm text-text-muted mb-1">Закрытие регистрации</label>
                <input type="datetime-local" value={form.registration_deadline} onChange={(e) => setForm({ ...form, registration_deadline: e.target.value })}
                  className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary" />
              </div>
              {!isEventPast(form.date_end) && (
                <div className="flex items-center gap-3 pt-5">
                  <input type="checkbox" id="reg_closed_edit" checked={form.registration_closed}
                    onChange={(e) => setForm({ ...form, registration_closed: e.target.checked })}
                    className="w-4 h-4 accent-danger cursor-pointer" />
                  <label htmlFor="reg_closed_edit" className="text-sm text-text cursor-pointer select-none">Закрыть регистрацию вручную</label>
                </div>
              )}
              <div className="sm:col-span-2">
                <label className="block text-sm text-text-muted mb-1">Место проведения</label>
                <input type="text" value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })}
                  placeholder="г. Уфа, СК «Уфа-Арена»"
                  className="w-full px-3 py-2 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary" />
              </div>
            </div>
            {formError && <p className="mt-3 text-danger text-sm">{formError}</p>}
            <div className="flex gap-3 mt-4">
              <button onClick={handleSave} disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-dark text-white rounded-lg text-sm font-medium transition-colors cursor-pointer border-none disabled:opacity-50">
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                Сохранить
              </button>
              <button onClick={() => setShowEditForm(false)}
                className="flex items-center gap-2 px-4 py-2 bg-surface border border-border hover:border-border-light text-text-muted rounded-lg text-sm font-medium transition-colors cursor-pointer">
                <X className="w-4 h-4" /> Отмена
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 flex-wrap mb-2">
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${DISCIPLINE_COLORS[competition.discipline] ?? 'bg-gray-500/15 text-gray-400'}`}>
                  {DISCIPLINE_LABEL[competition.discipline] ?? competition.discipline}
                </span>
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[competition.status] ?? 'bg-gray-500/15 text-gray-400'}`}>
                  {STATUS_LABEL[competition.status] ?? competition.status}
                </span>
                {competition.registration_closed && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-danger/15 text-danger">
                    <Lock className="w-2.5 h-2.5" /> Регистрация закрыта
                  </span>
                )}
              </div>
              <h1 className="text-xl font-bold text-text">{competition.name}</h1>
              <div className="text-text-muted text-sm mt-1 space-y-0.5">
                {(competition.date_start || competition.date_end) && (
                  <div>
                    {competition.date_start && new Date(competition.date_start).toLocaleDateString('ru-RU')}
                    {competition.date_end && competition.date_end !== competition.date_start && ` – ${new Date(competition.date_end).toLocaleDateString('ru-RU')}`}
                  </div>
                )}
                {competition.location && <div>{competition.location}</div>}
                {(competition.registration_open_at || competition.registration_deadline) && (
                  <div className="text-warning">
                    Приём заявок:
                    {competition.registration_open_at && ` с ${new Date(competition.registration_open_at).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}`}
                    {competition.registration_deadline && ` по ${new Date(competition.registration_deadline).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}`}
                  </div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button onClick={toggleRegClosed}
                className={`p-2 rounded-lg transition-colors cursor-pointer bg-transparent border border-border ${competition.registration_closed ? 'text-danger hover:bg-danger/10' : 'text-text-dim hover:text-success hover:bg-success/10'}`}
                title={competition.registration_closed ? 'Открыть регистрацию' : 'Закрыть регистрацию'}>
                {competition.registration_closed ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
              </button>
              <button onClick={openEdit}
                className="flex items-center gap-2 px-3 py-2 bg-surface border border-border hover:border-primary/50 text-text-muted hover:text-text rounded-lg text-sm transition-colors cursor-pointer">
                <Pencil className="w-4 h-4" /> Редактировать
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="bg-surface-light rounded-xl border border-border p-5 mb-6">
        <h3 className="text-sm font-semibold text-text-secondary mb-3 flex items-center gap-2">
          <FileSpreadsheet className="w-4 h-4 text-success" /> Скачать Excel-документы
        </h3>
        <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-2">
          {([
            { type: 'preliminary' as const, label: 'Предварительный список' },
            { type: 'weigh-in' as const, label: 'Список для взвешивания' },
            { type: 'brackets' as const, label: 'Полная сетка (Excel)' },
            { type: 'protocol' as const, label: 'Итоговый протокол' },
          ]).map(({ type, label }) => (
            <button key={type} onClick={() => handleDownload(type)} disabled={!!downloading}
              className="flex items-center gap-2 px-3 py-2.5 bg-surface border border-border rounded-lg text-text text-sm font-medium cursor-pointer hover:border-success/50 transition-colors disabled:opacity-50">
              {downloading === type ? <Loader2 className="w-4 h-4 text-success animate-spin" /> : <Download className="w-4 h-4 text-success" />}
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex border-b border-border mb-6">
        <button
          onClick={() => setActiveTab('participants')}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors cursor-pointer bg-transparent ${
            activeTab === 'participants' ? 'border-primary text-primary' : 'border-transparent text-text-muted hover:text-text'
          }`}>
          <Users className="w-4 h-4" /> Участники
        </button>
        <button
          onClick={() => setActiveTab('brackets')}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors cursor-pointer bg-transparent ${
            activeTab === 'brackets' ? 'border-primary text-primary' : 'border-transparent text-text-muted hover:text-text'
          }`}>
          <Trophy className="w-4 h-4" /> Сетки
        </button>
        <button
          onClick={() => setActiveTab('schedule')}
          className={`flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 transition-colors cursor-pointer bg-transparent ${
            activeTab === 'schedule' ? 'border-primary text-primary' : 'border-transparent text-text-muted hover:text-text'
          }`}>
          <CalendarDays className="w-4 h-4" /> Расписание
        </button>
      </div>

      {activeTab === 'participants' && (
        <ParticipantsTab competitionId={competitionId} />
      )}
      {activeTab === 'brackets' && (
        <BracketsTab competitionId={competitionId} />
      )}
      {activeTab === 'schedule' && (
        <AdminSchedule competitionId={competitionId} />
      )}
    </div>
  )
}

function ParticipantsTab({ competitionId }: { competitionId: number }) {
  const [participants, setParticipants] = useState<Participant[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [search, setSearch] = useState('')
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
  }, [])

  const load = useCallback(() => {
    setLoading(true)
    const params: { page: number; search?: string; competition_id: number } = { page, competition_id: competitionId }
    if (search) params.search = search
    adminApi.getParticipants(params).then((r) => {
      setParticipants(r.data.participants)
      setTotal(r.data.total)
      setTotalPages(r.data.total_pages)
      setLoading(false)
    })
  }, [page, search, competitionId])

  useEffect(() => { load() }, [load])

  const handleEdit = (p: Participant) => {
    setEditingId(p.id)
    setEditData({
      fio: p.fio, gender: p.gender, dob: p.dob || '',
      class_name: p.class_name || '', rank_name: p.rank_title || '',
      region_name: p.region_name || '', city_name: p.city_name || '',
      club_name: p.club_name || '', coach_name: p.coach_name || '',
    })
  }

  const handleSave = async () => {
    if (!editingId) return
    setSaving(true)
    try {
      await adminApi.updateParticipant(editingId, editData)
      setEditingId(null)
      load()
    } catch {}
    setSaving(false)
  }

  const handleDelete = async (id: number) => {
    try {
      await adminApi.deleteParticipant(id)
      setDeleteConfirm(null)
      load()
    } catch {}
  }

  const handleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setCsvUploading(true)
    setCsvResult(null)
    try {
      const res = await adminApi.importCsv(file, competitionId)
      setCsvResult(res.data)
      load()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setCsvResult({ errors: -1, error_details: [err.response?.data?.detail || 'Ошибка'] })
    }
    setCsvUploading(false)
    e.target.value = ''
  }

  const inputCls = "w-full px-3 py-2 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none"

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-text-muted text-sm">Всего участников: {total}</p>
        <label className="flex items-center gap-2 px-4 py-2 bg-accent/10 border border-accent/30 text-accent rounded-lg text-sm font-medium cursor-pointer hover:bg-accent/20 transition-colors">
          <Upload className="w-4 h-4" />
          {csvUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Импорт CSV'}
          <input type="file" accept=".csv" onChange={handleCsvUpload} className="hidden" />
        </label>
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

      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
        <input
          type="text" placeholder="Поиск по ФИО..." value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          className="w-full pl-10 pr-4 py-3 bg-surface-light border border-border rounded-xl text-text placeholder:text-text-muted focus:outline-none focus:border-primary/50 transition-colors"
        />
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
                  {classes.map((c) => <option key={c.id} value={c.name}>{c.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">Разряд</label>
                <select value={editData.rank_name || ''} onChange={(e) => setEditData({ ...editData, rank_name: e.target.value })} className={inputCls}>
                  <option value="">—</option>
                  {ranks.map((r) => <option key={r.id} value={r.name}>{r.name}</option>)}
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

function BracketsTab({ competitionId }: { competitionId: number }) {
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<Category | null>(null)
  const [bracket, setBracket] = useState<(BracketParticipant | null)[]>([])
  const [isApproved, setIsApproved] = useState(false)
  const [swapFrom, setSwapFrom] = useState<number | null>(null)
  const [actionLoading, setActionLoading] = useState(false)
  const [bracketImageUrl, setBracketImageUrl] = useState('')

  const loadCategories = useCallback(() => {
    setLoading(true)
    setSelected(null)
    adminApi.getBracketCategories(competitionId).then((r) => {
      setCategories(r.data)
      setLoading(false)
    })
  }, [competitionId])

  useEffect(() => { loadCategories() }, [loadCategories])

  const buildParams = (cat: Category) => ({
    class_name: cat.class_name,
    gender: cat.gender,
    age_category_name: cat.age_category_name,
    weight_name: cat.weight_name,
    competition_id: competitionId,
  })

  const selectCategory = useCallback(async (cat: Category) => {
    setSelected(cat)
    setSwapFrom(null)
    setActionLoading(true)
    try {
      const params = buildParams(cat)
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
    if (swapFrom === null) { setSwapFrom(index); return }
    if (swapFrom === index) { setSwapFrom(null); return }
    setActionLoading(true)
    try {
      await adminApi.swapParticipants({ ...buildParams(selected), index_a: swapFrom, index_b: index })
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
      loadCategories()
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
      <div>
        <button onClick={() => setSelected(null)} className="flex items-center gap-2 text-text-muted hover:text-text mb-4 cursor-pointer bg-transparent border-none text-sm">
          <ChevronLeft className="w-4 h-4" /> Назад к списку
        </button>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-bold">{selected.class_name} - {selected.gender}</h2>
            <p className="text-text-secondary text-sm">{selected.age_category_name}, {selected.weight_name} kg</p>
          </div>
          <span className={`px-3 py-1 rounded-full text-xs font-medium ${isApproved ? 'bg-success/10 text-success' : 'bg-surface-lighter text-text-muted'}`}>
            {isApproved ? 'Утверждено' : 'Не утверждено'}
          </span>
        </div>
        <div className="grid lg:grid-cols-[300px_1fr] gap-6">
          <div className="space-y-4">
            <div className="bg-surface-light rounded-xl border border-border p-4">
              <h3 className="text-sm font-semibold text-text-secondary mb-3">Участники (нажмите для swap)</h3>
              <div className="space-y-1">
                {bracket.map((p, i) => (
                  <button key={i} onClick={() => p && handleSwap(i)} disabled={!p || actionLoading}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm border transition-all ${
                      !p ? 'bg-surface-lighter/30 text-text-muted border-transparent cursor-default' :
                      swapFrom === i ? 'bg-accent/10 border-accent/50 text-accent cursor-pointer' :
                      'bg-surface border-border hover:border-primary/30 text-text cursor-pointer'
                    }`}>
                    {p ? (
                      <div>
                        <div className="font-medium">{p.fio}</div>
                        <div className="text-xs text-text-muted">{p.club_name}</div>
                      </div>
                    ) : <span className="text-text-muted italic">BYE</span>}
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
              <button onClick={() => adminApi.downloadBracketPng(buildParams(selected)).catch(() => {})} disabled={actionLoading}
                className="flex items-center justify-center gap-2 py-2.5 bg-surface-light border border-border rounded-lg text-text-secondary text-sm font-medium cursor-pointer hover:border-success/30 transition-colors disabled:opacity-50">
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

  if (loading) return <div className="text-center py-12 text-text-muted">Загрузка...</div>

  if (categories.length === 0) return (
    <div className="text-center py-16">
      <Trophy className="w-16 h-16 mx-auto mb-4 text-text-muted" />
      <p className="text-text-muted text-lg mb-2">Нет категорий с участниками</p>
      <p className="text-text-muted text-sm">Добавьте участников на вкладке «Участники», чтобы сгенерировать сетки</p>
    </div>
  )

  return (
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
                {c.approved
                  ? <span className="flex items-center gap-1 text-success text-xs"><Check className="w-3 h-3" /> Утверждено</span>
                  : <span className="text-text-muted text-xs">Не утверждено</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}


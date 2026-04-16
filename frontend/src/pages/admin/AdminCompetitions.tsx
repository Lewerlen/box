import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api, { competitionsApi } from '../../api'
import { Plus, Pencil, Trash2, Loader2, X, Check, Lock, Unlock, Settings, Clock } from 'lucide-react'

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

const DISCIPLINE_OPTIONS = [
  { value: 'muay_thai', label: 'Тайский бокс' },
  { value: 'kickboxing', label: 'Кикбоксинг' },
]

const STATUS_OPTIONS = [
  { value: 'upcoming', label: 'Скоро' },
  { value: 'active', label: 'Идёт регистрация' },
  { value: 'finished', label: 'Завершено' },
]

const DISCIPLINE_LABEL: Record<string, string> = {
  muay_thai: 'Тайский бокс',
  kickboxing: 'Кикбоксинг',
}

const DISCIPLINE_COLORS: Record<string, string> = {
  muay_thai: 'bg-red-500/15 text-red-400 border border-red-500/30',
  kickboxing: 'bg-blue-500/15 text-blue-400 border border-blue-500/30',
}

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

function formatDateTime(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
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

export default function AdminCompetitions() {
  const navigate = useNavigate()
  const [competitions, setCompetitions] = useState<Competition[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState<number | null>(null)
  const [form, setForm] = useState({ ...emptyForm })
  const [initialForm, setInitialForm] = useState({ ...emptyForm })
  const [saving, setSaving] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [error, setError] = useState('')

  const isDirty = showForm && JSON.stringify(form) !== JSON.stringify(initialForm)

  useEffect(() => {
    if (!isDirty) return
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [isDirty])

  const load = () => {
    api.get('/admin/competitions')
      .then((r) => setCompetitions(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const confirmDiscardIfDirty = () =>
    !isDirty || window.confirm('Есть несохранённые изменения. Закрыть без сохранения?')

  const openCreate = () => {
    if (!confirmDiscardIfDirty()) return
    setEditId(null)
    setForm({ ...emptyForm })
    setInitialForm({ ...emptyForm })
    setError('')
    setShowForm(true)
  }

  const openEdit = (c: Competition) => {
    if (!confirmDiscardIfDirty()) return
    setEditId(c.id)
    const formValues = {
      name: c.name,
      discipline: c.discipline,
      date_start: c.date_start ?? '',
      date_end: c.date_end ?? '',
      location: c.location ?? '',
      status: c.status,
      registration_deadline: toDateTimeLocal(c.registration_deadline),
      registration_open_at: toDateTimeLocal(c.registration_open_at),
      registration_closed: c.registration_closed,
    }
    setForm(formValues)
    setInitialForm(formValues)
    setError('')
    setShowForm(true)
  }

  const handleCancel = () => {
    if (!confirmDiscardIfDirty()) return
    setShowForm(false)
  }

  const handleSave = async () => {
    if (!form.name.trim()) {
      setError('Введите название соревнования')
      return
    }
    setSaving(true)
    setError('')
    try {
      const payload = {
        name: form.name.trim(),
        discipline: form.discipline,
        date_start: form.date_start || undefined,
        date_end: form.date_end || undefined,
        location: form.location.trim() || undefined,
        status: form.status,
        registration_deadline: fromDateTimeLocal(form.registration_deadline),
        registration_open_at: fromDateTimeLocal(form.registration_open_at),
        registration_closed: form.registration_closed,
      }
      if (editId !== null) {
        await competitionsApi.update(editId, payload)
      } else {
        await competitionsApi.create(payload)
      }
      setShowForm(false)
      load()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(err.response?.data?.detail ?? 'Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить соревнование?')) return
    setDeletingId(id)
    try {
      await competitionsApi.delete(id)
      load()
    } catch {}
    setDeletingId(null)
  }

  const toggleRegClosed = async (c: Competition) => {
    const msg = c.registration_closed ? 'Открыть регистрацию?' : 'Закрыть регистрацию?'
    if (!confirm(msg)) return
    try {
      await competitionsApi.update(c.id, { registration_closed: !c.registration_closed })
      load()
    } catch {}
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-text">Соревнования</h1>
        {!showForm && (
          <button
            onClick={openCreate}
            className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent-dark text-white rounded-lg text-sm font-medium transition-colors cursor-pointer border-none"
          >
            <Plus className="w-4 h-4" />
            Добавить
          </button>
        )}
      </div>

      {showForm && (
        <div className="bg-surface border border-border-light rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4 text-text">
            {editId !== null ? 'Редактировать соревнование' : 'Новое соревнование'}
          </h2>

          <div className="grid sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-sm text-text-muted mb-1">Название *</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Чемпионат Республики..."
                className="w-full px-3 py-2 bg-surface-light border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary"
              />
            </div>

            <div>
              <label className="block text-sm text-text-muted mb-1">Дисциплина</label>
              <select
                value={form.discipline}
                onChange={(e) => setForm({ ...form, discipline: e.target.value })}
                className="w-full px-3 py-2 bg-surface-light border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary"
              >
                {DISCIPLINE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-text-muted mb-1">Статус</label>
              <select
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
                className="w-full px-3 py-2 bg-surface-light border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary"
              >
                {STATUS_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-text-muted mb-1">Дата начала</label>
              <input
                type="date"
                value={form.date_start}
                onChange={(e) => setForm({ ...form, date_start: e.target.value })}
                className="w-full px-3 py-2 bg-surface-light border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary"
              />
            </div>

            <div>
              <label className="block text-sm text-text-muted mb-1">Дата окончания</label>
              <input
                type="date"
                value={form.date_end}
                onChange={(e) => setForm({ ...form, date_end: e.target.value })}
                className="w-full px-3 py-2 bg-surface-light border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary"
              />
            </div>

            <div>
              <label className="block text-sm text-text-muted mb-1">Открытие регистрации</label>
              <input
                type="datetime-local"
                value={form.registration_open_at}
                onChange={(e) => setForm({ ...form, registration_open_at: e.target.value })}
                className="w-full px-3 py-2 bg-surface-light border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary"
              />
            </div>

            <div>
              <label className="block text-sm text-text-muted mb-1">Закрытие регистрации</label>
              <input
                type="datetime-local"
                value={form.registration_deadline}
                onChange={(e) => setForm({ ...form, registration_deadline: e.target.value })}
                className="w-full px-3 py-2 bg-surface-light border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary"
              />
            </div>

            {editId !== null && !isEventPast(form.date_end) && (
              <div className="flex items-center gap-3 pt-5">
                <input
                  type="checkbox"
                  id="reg_closed"
                  checked={form.registration_closed}
                  onChange={(e) => setForm({ ...form, registration_closed: e.target.checked })}
                  className="w-4 h-4 accent-danger cursor-pointer"
                />
                <label htmlFor="reg_closed" className="text-sm text-text cursor-pointer select-none">
                  Закрыть регистрацию вручную
                </label>
              </div>
            )}

            <div className={editId !== null ? '' : 'sm:col-span-2'}>
              <label className="block text-sm text-text-muted mb-1">Место проведения</label>
              <input
                type="text"
                value={form.location}
                onChange={(e) => setForm({ ...form, location: e.target.value })}
                placeholder="г. Уфа, СК «Уфа-Арена»"
                className="w-full px-3 py-2 bg-surface-light border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary"
              />
            </div>
          </div>

          {error && <p className="mt-3 text-danger text-sm">{error}</p>}

          <div className="flex gap-3 mt-4">
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-dark text-white rounded-lg text-sm font-medium transition-colors cursor-pointer border-none disabled:opacity-50"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              {editId !== null ? 'Сохранить' : 'Создать'}
            </button>
            <button
              onClick={handleCancel}
              className="flex items-center gap-2 px-4 py-2 bg-surface-light border border-border hover:border-border-light text-text-muted rounded-lg text-sm font-medium transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
              Отмена
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-text-muted">Загрузка...</div>
      ) : competitions.length === 0 ? (
        <div className="text-center py-12 text-text-muted">Нет соревнований. Добавьте первое!</div>
      ) : (
        <div className="space-y-3">
          {competitions.map((c) => (
            <div
              key={c.id}
              className="bg-surface border border-border-light rounded-xl p-4 flex items-start gap-4"
            >
              <div className="flex flex-col gap-1.5 shrink-0 mt-0.5">
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${DISCIPLINE_COLORS[c.discipline] ?? 'bg-gray-500/15 text-gray-400'}`}>
                  {DISCIPLINE_LABEL[c.discipline] ?? c.discipline}
                </span>
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[c.status] ?? 'bg-gray-500/15 text-gray-400'}`}>
                  {STATUS_LABEL[c.status] ?? c.status}
                </span>
                {c.registration_closed && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-danger/15 text-danger">
                    <Lock className="w-2.5 h-2.5" />
                    Закрыта
                  </span>
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="font-medium text-text text-sm leading-snug">{c.name}</div>
                <div className="text-text-muted text-xs mt-1 space-y-0.5">
                  {(c.date_start || c.date_end) && (
                    <div>
                      {c.date_start && new Date(c.date_start).toLocaleDateString('ru-RU')}
                      {c.date_end && c.date_end !== c.date_start && ` – ${new Date(c.date_end).toLocaleDateString('ru-RU')}`}
                    </div>
                  )}
                  {c.location && <div>{c.location}</div>}
                  {(c.registration_open_at || c.registration_deadline) && (
                    <div className="flex items-center gap-1 text-warning">
                      <Clock className="w-3 h-3" />
                      <span>
                        Приём заявок:
                        {c.registration_open_at ? ` с ${formatDateTime(c.registration_open_at)}` : ''}
                        {c.registration_deadline ? ` по ${formatDateTime(c.registration_deadline)}` : ''}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-1 shrink-0">
                <button
                  onClick={() => navigate(`/admin/competitions/${c.id}`)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-accent border border-accent/30 hover:bg-accent/10 rounded-lg transition-colors cursor-pointer bg-transparent"
                  title="Управление соревнованием"
                >
                  <Settings className="w-3.5 h-3.5" /> Управление
                </button>
                {!isEventPast(c.date_end) && (
                  <button
                    onClick={() => toggleRegClosed(c)}
                    className={`p-2 rounded-lg transition-colors cursor-pointer bg-transparent border-none ${c.registration_closed ? 'text-danger hover:bg-danger/10' : 'text-text-dim hover:text-success hover:bg-success/10'}`}
                    title={c.registration_closed ? 'Открыть регистрацию' : 'Закрыть регистрацию'}
                  >
                    {c.registration_closed ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
                  </button>
                )}
                <button
                  onClick={() => openEdit(c)}
                  className="p-2 text-text-dim hover:text-primary hover:bg-primary/10 rounded-lg transition-colors cursor-pointer bg-transparent border-none"
                  title="Редактировать"
                >
                  <Pencil className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDelete(c.id)}
                  disabled={deletingId === c.id}
                  className="p-2 text-text-dim hover:text-danger hover:bg-danger/10 rounded-lg transition-colors cursor-pointer bg-transparent border-none disabled:opacity-50"
                  title="Удалить"
                >
                  {deletingId === c.id
                    ? <Loader2 className="w-4 h-4 animate-spin" />
                    : <Trash2 className="w-4 h-4" />}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

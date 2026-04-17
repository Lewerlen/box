import { useEffect, useState, useCallback } from 'react'
import { adminApi } from '../../api'
import { ChevronRight, Plus, Edit3, Trash2, GitMerge, X, Search, Loader2, Users } from 'lucide-react'

interface RefEntry {
  id: number
  name: string
  count: number
}

interface BreadcrumbItem {
  label: string
  level: string
  parentId?: number
}

const LEVELS = [
  { key: 'regions', label: 'Регионы', singular: 'регион', parentLabel: '' },
  { key: 'cities', label: 'Города', singular: 'город', parentLabel: 'региона' },
  { key: 'clubs', label: 'Клубы', singular: 'клуб', parentLabel: 'города' },
  { key: 'coaches', label: 'Тренеры', singular: 'тренер', parentLabel: 'клуба' },
]

export default function AdminReferences() {
  const [level, setLevel] = useState(0)
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbItem[]>([{ label: 'Регионы', level: 'regions' }])
  const [items, setItems] = useState<RefEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [parentId, setParentId] = useState<number | undefined>(undefined)

  const [editingId, setEditingId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [addingNew, setAddingNew] = useState(false)
  const [newName, setNewName] = useState('')

  const [mergeSource, setMergeSource] = useState<RefEntry | null>(null)
  const [mergeSearch, setMergeSearch] = useState('')
  const [mergeTargetId, setMergeTargetId] = useState<number | null>(null)
  const [merging, setMerging] = useState(false)

  const [deleteTarget, setDeleteTarget] = useState<RefEntry | null>(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const loadItems = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      let res
      if (level === 0) res = await adminApi.getRefRegions()
      else if (level === 1) res = await adminApi.getRefCities(parentId!)
      else if (level === 2) res = await adminApi.getRefClubs(parentId!)
      else res = await adminApi.getRefCoaches(parentId!)
      const sorted = [...res.data].sort((a: RefEntry, b: RefEntry) => {
        if (b.count !== a.count) return b.count - a.count
        return a.name.localeCompare(b.name, 'ru')
      })
      setItems(sorted)
    } catch {
      setError('Ошибка загрузки')
    }
    setLoading(false)
  }, [level, parentId])

  useEffect(() => { loadItems() }, [loadItems])

  const drillDown = (item: RefEntry) => {
    if (level >= 3) return
    const nextLevel = level + 1
    setBreadcrumbs([...breadcrumbs, { label: item.name, level: LEVELS[nextLevel].key, parentId: item.id }])
    setParentId(item.id)
    setLevel(nextLevel)
  }

  const goToLevel = (index: number) => {
    const newBreadcrumbs = breadcrumbs.slice(0, index + 1)
    setBreadcrumbs(newBreadcrumbs)
    setLevel(index)
    setParentId(newBreadcrumbs[index].parentId)
  }

  const handleRename = async () => {
    if (!editingId || !editName.trim()) return
    setSaving(true)
    try {
      await adminApi.renameRef(LEVELS[level].key, editingId, editName.trim())
      setEditingId(null)
      setEditName('')
      loadItems()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(err.response?.data?.detail || 'Ошибка переименования')
    }
    setSaving(false)
  }

  const handleCreate = async () => {
    if (!newName.trim()) return
    setSaving(true)
    try {
      await adminApi.createRef(LEVELS[level].key, newName.trim(), parentId)
      setAddingNew(false)
      setNewName('')
      loadItems()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(err.response?.data?.detail || 'Ошибка создания')
    }
    setSaving(false)
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    setSaving(true)
    try {
      await adminApi.deleteRef(LEVELS[level].key, deleteTarget.id)
      setDeleteTarget(null)
      loadItems()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(err.response?.data?.detail || 'Ошибка удаления')
    }
    setSaving(false)
  }

  const handleMerge = async () => {
    if (!mergeSource || !mergeTargetId) return
    setMerging(true)
    try {
      await adminApi.mergeRef(LEVELS[level].key, mergeSource.id, mergeTargetId)
      setMergeSource(null)
      setMergeSearch('')
      setMergeTargetId(null)
      loadItems()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(err.response?.data?.detail || 'Ошибка объединения')
    }
    setMerging(false)
  }

  const mergeOptions = items.filter(
    (i) => i.id !== mergeSource?.id && i.name.toLowerCase().includes(mergeSearch.toLowerCase())
  )

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-2">Справочники</h1>
      <p className="text-text-muted text-sm mb-6">Регионы, города, клубы и тренеры</p>

      <nav className="flex items-center gap-1 mb-6 flex-wrap">
        {breadcrumbs.map((bc, i) => (
          <span key={i} className="flex items-center gap-1">
            {i > 0 && <ChevronRight className="w-4 h-4 text-text-muted" />}
            <button
              onClick={() => goToLevel(i)}
              className={`text-sm font-medium px-2 py-1 rounded cursor-pointer border-none transition-colors ${
                i === breadcrumbs.length - 1
                  ? 'bg-primary/10 text-primary'
                  : 'bg-transparent text-text-muted hover:text-text'
              }`}
            >
              {bc.label}
            </button>
          </span>
        ))}
      </nav>

      {error && (
        <div className="bg-danger/10 border border-danger/30 text-danger rounded-lg px-4 py-3 mb-4 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError('')} className="bg-transparent border-none text-danger cursor-pointer"><X className="w-4 h-4" /></button>
        </div>
      )}

      <div className="bg-surface rounded-xl border border-border-light shadow-sm">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border-light">
          <h2 className="text-lg font-semibold">{LEVELS[level].label}</h2>
          <button
            onClick={() => { setAddingNew(true); setNewName('') }}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-primary text-white text-sm font-medium rounded-lg cursor-pointer border-none hover:bg-primary-dark transition-colors"
          >
            <Plus className="w-4 h-4" /> Добавить
          </button>
        </div>

        {addingNew && (
          <div className="px-5 py-3 border-b border-border-light bg-surface-light flex items-center gap-3">
            <input
              value={newName} onChange={(e) => setNewName(e.target.value)} placeholder={`Новый ${LEVELS[level].singular}...`}
              className="flex-1 px-3 py-2 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary/50"
              onKeyDown={(e) => { if (e.key === 'Enter') handleCreate(); if (e.key === 'Escape') setAddingNew(false) }}
              autoFocus
            />
            <button onClick={handleCreate} disabled={saving || !newName.trim()}
              className="px-4 py-2 bg-primary text-white text-sm rounded-lg cursor-pointer border-none disabled:opacity-50 hover:bg-primary-dark transition-colors font-medium">
              {saving ? '...' : 'Создать'}
            </button>
            <button onClick={() => setAddingNew(false)}
              className="p-2 text-text-muted hover:text-text bg-transparent border-none cursor-pointer"><X className="w-4 h-4" /></button>
          </div>
        )}

        {loading ? (
          <div className="px-5 py-12 text-center text-text-muted">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
            Загрузка...
          </div>
        ) : items.length === 0 ? (
          <div className="px-5 py-12 text-center text-text-muted">Нет записей</div>
        ) : (
          <div>
            {items.map((item) => (
              <div key={item.id} className="flex items-center gap-3 px-5 py-3 border-b border-border/30 last:border-b-0 hover:bg-surface-lighter/30 transition-colors group">
                {editingId === item.id ? (
                  <div className="flex-1 flex items-center gap-2">
                    <input value={editName} onChange={(e) => setEditName(e.target.value)}
                      className="flex-1 px-3 py-1.5 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary/50"
                      onKeyDown={(e) => { if (e.key === 'Enter') handleRename(); if (e.key === 'Escape') setEditingId(null) }}
                      autoFocus
                    />
                    <button onClick={handleRename} disabled={saving}
                      className="px-3 py-1.5 bg-primary text-white text-xs rounded cursor-pointer border-none font-medium">Ок</button>
                    <button onClick={() => setEditingId(null)}
                      className="p-1.5 text-text-muted hover:text-text bg-transparent border-none cursor-pointer"><X className="w-3.5 h-3.5" /></button>
                  </div>
                ) : (
                  <>
                    <button
                      onClick={() => level < 3 ? drillDown(item) : undefined}
                      className={`flex-1 text-left text-sm font-medium bg-transparent border-none transition-colors ${
                        level < 3 ? 'cursor-pointer text-text hover:text-primary' : 'cursor-default text-text'
                      }`}
                    >
                      {item.name}
                    </button>
                    <span className="flex items-center gap-1 text-xs text-text-muted px-2 py-1 bg-surface-lighter rounded-full">
                      <Users className="w-3 h-3" /> {item.count}
                    </span>
                    {level < 3 && (
                      <ChevronRight className="w-4 h-4 text-text-muted opacity-0 group-hover:opacity-100 transition-opacity" />
                    )}
                    <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button onClick={() => { setEditingId(item.id); setEditName(item.name) }}
                        title="Переименовать"
                        className="p-1.5 rounded hover:bg-surface-lighter text-text-muted hover:text-accent cursor-pointer bg-transparent border-none transition-colors">
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => setMergeSource(item)}
                        title="Объединить с другим"
                        className="p-1.5 rounded hover:bg-surface-lighter text-text-muted hover:text-primary cursor-pointer bg-transparent border-none transition-colors">
                        <GitMerge className="w-3.5 h-3.5" />
                      </button>
                      <button onClick={() => item.count > 0 ? setError(`Нельзя удалить «${item.name}»: ${item.count} участник(ов) привязано. Используйте объединение.`) : setDeleteTarget(item)}
                        title="Удалить"
                        className="p-1.5 rounded hover:bg-surface-lighter text-text-muted hover:text-danger cursor-pointer bg-transparent border-none transition-colors">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {mergeSource && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
          <div className="bg-surface-light rounded-xl border border-border p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Объединить записи</h3>
              <button onClick={() => { setMergeSource(null); setMergeSearch(''); setMergeTargetId(null) }}
                className="text-text-muted hover:text-text cursor-pointer bg-transparent border-none"><X className="w-5 h-5" /></button>
            </div>

            <div className="bg-danger/10 border border-danger/20 rounded-lg px-4 py-3 mb-4">
              <p className="text-sm text-danger font-medium">Удалить:</p>
              <p className="text-sm text-text mt-1">«{mergeSource.name}» ({mergeSource.count} участник(ов))</p>
            </div>

            <p className="text-sm text-text-secondary mb-3">Перенести участников в:</p>

            <div className="relative mb-3">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
              <input value={mergeSearch} onChange={(e) => { setMergeSearch(e.target.value); setMergeTargetId(null) }}
                placeholder="Поиск..."
                className="w-full pl-9 pr-4 py-2.5 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none focus:border-primary/50"
              />
            </div>

            <div className="max-h-48 overflow-y-auto border border-border rounded-lg" style={{ scrollbarWidth: 'thin', scrollbarColor: 'var(--color-border) var(--color-surface-light)' }}>
              {mergeOptions.length === 0 ? (
                <div className="px-4 py-6 text-center text-text-muted text-sm">Нет подходящих записей</div>
              ) : (
                mergeOptions.map((opt) => (
                  <button key={opt.id} onClick={() => setMergeTargetId(opt.id)}
                    className={`w-full px-4 py-2.5 text-left text-sm border-none cursor-pointer transition-colors flex items-center justify-between ${
                      mergeTargetId === opt.id ? 'bg-primary/15 text-primary font-semibold' : 'bg-transparent text-text hover:bg-surface-lighter'
                    }`}>
                    <span>{opt.name}</span>
                    <span className="text-xs text-text-muted">{opt.count}</span>
                  </button>
                ))
              )}
            </div>

            <div className="flex gap-3 mt-4">
              <button onClick={() => { setMergeSource(null); setMergeSearch(''); setMergeTargetId(null) }}
                className="flex-1 py-2.5 bg-surface border border-border rounded-lg text-text-secondary cursor-pointer text-sm font-medium">Отмена</button>
              <button onClick={handleMerge} disabled={!mergeTargetId || merging}
                className="flex-1 py-2.5 bg-primary text-white rounded-lg cursor-pointer border-none text-sm font-medium disabled:opacity-50 hover:bg-primary-dark transition-colors">
                {merging ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : 'Объединить'}
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteTarget && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
          <div className="bg-surface-light rounded-xl border border-border p-6 w-full max-w-sm text-center">
            <Trash2 className="w-12 h-12 text-danger mx-auto mb-3" />
            <h3 className="text-lg font-semibold mb-2">Удалить «{deleteTarget.name}»?</h3>
            <p className="text-text-muted text-sm mb-4">Это действие нельзя отменить</p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteTarget(null)} className="flex-1 py-2 bg-surface border border-border rounded-lg text-text-secondary cursor-pointer">Отмена</button>
              <button onClick={handleDelete} disabled={saving}
                className="flex-1 py-2 bg-danger text-white rounded-lg font-medium cursor-pointer border-none disabled:opacity-50">
                {saving ? '...' : 'Удалить'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

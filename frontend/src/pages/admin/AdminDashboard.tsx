import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { publicApi, adminApi } from '../../api'
import { Users, Trophy, FileSpreadsheet, Download, Loader2, BookOpen } from 'lucide-react'

interface TournamentStats {
  total_participants: number
  total_clubs: number
  total_regions: number
  male_count: number
  female_count: number
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<TournamentStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [downloading, setDownloading] = useState('')

  useEffect(() => {
    publicApi.getStats().then((r) => setStats(r.data)).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const handleDownload = async (type: 'preliminary' | 'weigh-in' | 'brackets' | 'protocol') => {
    setDownloading(type)
    try {
      await adminApi.downloadExcel(type)
    } catch {}
    setDownloading('')
  }

  if (loading) return <div className="text-center py-12 text-text-muted">Загрузка...</div>

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Панель администратора</h1>

      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'Участников', value: stats.total_participants, color: 'text-primary' },
            { label: 'Клубов', value: stats.total_clubs, color: 'text-accent' },
            { label: 'Регионов', value: stats.total_regions, color: 'text-success' },
            { label: 'Муж / Жен', value: `${stats.male_count} / ${stats.female_count}`, color: 'text-primary-light' },
          ].map((s, i) => (
            <div key={i} className="bg-surface-light rounded-xl border border-border p-5 text-center">
              <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
              <div className="text-text-muted text-sm mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Link to="/admin/competitions" className="bg-surface-light rounded-xl border border-border p-6 hover:border-yellow-500/50 transition-colors no-underline group">
          <Trophy className="w-8 h-8 text-yellow-500 mb-3" />
          <h3 className="text-lg font-semibold text-text">Соревнования</h3>
          <p className="text-text-muted text-sm mt-1">Создание и управление соревнованиями</p>
        </Link>
        <Link to="/admin/participants" className="bg-surface-light rounded-xl border border-border p-6 hover:border-primary/50 transition-colors no-underline group">
          <Users className="w-8 h-8 text-primary mb-3" />
          <h3 className="text-lg font-semibold text-text">Участники</h3>
          <p className="text-text-muted text-sm mt-1">Просмотр, редактирование, импорт CSV</p>
        </Link>
        <Link to="/admin/brackets" className="bg-surface-light rounded-xl border border-border p-6 hover:border-accent/50 transition-colors no-underline group">
          <Trophy className="w-8 h-8 text-accent mb-3" />
          <h3 className="text-lg font-semibold text-text">Сетки</h3>
          <p className="text-text-muted text-sm mt-1">Генерация, swap, утверждение сеток</p>
        </Link>
        <Link to="/admin/references" className="bg-surface-light rounded-xl border border-border p-6 hover:border-success/50 transition-colors no-underline group">
          <BookOpen className="w-8 h-8 text-success mb-3" />
          <h3 className="text-lg font-semibold text-text">Справочники</h3>
          <p className="text-text-muted text-sm mt-1">Регионы, города, клубы, тренеры</p>
        </Link>
      </div>

      <div className="bg-surface-light rounded-xl border border-border p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <FileSpreadsheet className="w-5 h-5 text-success" />
          Скачать Excel-документы
        </h3>
        <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-3">
          {([
            { type: 'preliminary' as const, label: 'Предварительный список' },
            { type: 'weigh-in' as const, label: 'Список для взвешивания' },
            { type: 'brackets' as const, label: 'Полная сетка (Excel)' },
            { type: 'protocol' as const, label: 'Итоговый протокол' },
          ]).map(({ type, label }) => (
            <button
              key={type}
              onClick={() => handleDownload(type)}
              disabled={!!downloading}
              className="flex items-center gap-2 px-4 py-3 bg-surface border border-border rounded-lg text-text text-sm font-medium cursor-pointer hover:border-success/50 transition-colors disabled:opacity-50"
            >
              {downloading === type ? <Loader2 className="w-4 h-4 text-success animate-spin" /> : <Download className="w-4 h-4 text-success" />}
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

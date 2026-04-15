import { useEffect, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { publicApi } from '../api'
import { Search, ChevronLeft, ChevronRight, Filter, X } from 'lucide-react'

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

export default function ParticipantsPage() {
  const { id: competitionId } = useParams<{ id?: string }>()
  const [participants, setParticipants] = useState<Participant[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [search, setSearch] = useState('')
  const [gender, setGender] = useState('')
  const [ageCategoryId, setAgeCategoryId] = useState('')
  const [weightCategoryId, setWeightCategoryId] = useState('')
  const [classId, setClassId] = useState('')
  const [clubId, setClubId] = useState('')
  const [regionId, setRegionId] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [ageCategories, setAgeCategories] = useState<RefItem[]>([])
  const [weightCategories, setWeightCategories] = useState<RefItem[]>([])
  const [classes, setClasses] = useState<RefItem[]>([])
  const [clubs, setClubs] = useState<RefItem[]>([])
  const [regions, setRegions] = useState<RefItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    publicApi.getAgeCategories().then((r) => setAgeCategories(r.data))
    publicApi.getClasses().then((r) => setClasses(r.data))
    publicApi.getClubs().then((r) => setClubs(r.data))
    publicApi.getRegions().then((r) => setRegions(r.data))
  }, [])

  useEffect(() => {
    if (ageCategoryId) {
      publicApi.getWeightCategories(Number(ageCategoryId)).then((r) => setWeightCategories(r.data))
    } else {
      setWeightCategories([])
      setWeightCategoryId('')
    }
  }, [ageCategoryId])

  const load = useCallback(() => {
    setLoading(true)
    const params: Record<string, string | number> = { page }
    if (search) params.search = search
    if (gender) params.gender = gender
    if (ageCategoryId) params.age_category_id = ageCategoryId
    if (weightCategoryId) params.weight_category_id = weightCategoryId
    if (classId) params.class_id = classId
    if (clubId) params.club_id = clubId
    if (regionId) params.region_id = regionId
    if (competitionId) params.competition_id = competitionId
    publicApi.getParticipants(params).then((r) => {
      setParticipants(r.data.participants)
      setTotal(r.data.total)
      setTotalPages(r.data.total_pages)
      setLoading(false)
    })
  }, [page, search, gender, ageCategoryId, weightCategoryId, classId, clubId, regionId, competitionId])

  useEffect(() => { load() }, [load])

  const clearFilters = () => {
    setGender('')
    setAgeCategoryId('')
    setWeightCategoryId('')
    setClassId('')
    setClubId('')
    setRegionId('')
    setSearch('')
    setPage(1)
  }

  const hasFilters = gender || ageCategoryId || weightCategoryId || classId || clubId || regionId

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
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Участники</h1>
          <p className="text-text-muted text-sm mt-1">Всего: {total}</p>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border text-sm font-medium cursor-pointer transition-colors ${
            hasFilters ? 'bg-primary/10 border-primary/30 text-primary' : 'bg-surface-light border-border text-text-secondary hover:text-text'
          }`}
        >
          <Filter className="w-4 h-4" />
          Фильтры
          {hasFilters && (
            <span className="bg-primary text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
              {[gender, ageCategoryId, weightCategoryId, classId, clubId, regionId].filter(Boolean).length}
            </span>
          )}
        </button>
      </div>

      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
        <input
          type="text"
          placeholder="Поиск по ФИО..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          className="w-full pl-10 pr-4 py-3 bg-surface-light border border-border rounded-xl text-text placeholder:text-text-muted focus:outline-none focus:border-primary/50 transition-colors"
        />
      </div>

      {showFilters && (
        <div className="bg-surface-light rounded-xl border border-border p-4 mb-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          <select
            value={gender}
            onChange={(e) => { setGender(e.target.value); setPage(1) }}
            className="px-3 py-2 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none"
          >
            <option value="">Все (пол)</option>
            <option value="Мужской">Мужской</option>
            <option value="Женский">Женский</option>
          </select>
          <select
            value={ageCategoryId}
            onChange={(e) => { setAgeCategoryId(e.target.value); setWeightCategoryId(''); setPage(1) }}
            className="px-3 py-2 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none"
          >
            <option value="">Все возраст. кат.</option>
            {ageCategories.map((c) => (
              <option key={c.id} value={c.id}>{c.name} ({c.gender})</option>
            ))}
          </select>
          <select
            value={weightCategoryId}
            onChange={(e) => { setWeightCategoryId(e.target.value); setPage(1) }}
            disabled={!ageCategoryId}
            className="px-3 py-2 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none disabled:opacity-50"
          >
            <option value="">Все весовые кат.</option>
            {weightCategories.map((w) => (
              <option key={w.id} value={w.id}>{w.name}</option>
            ))}
          </select>
          <select
            value={classId}
            onChange={(e) => { setClassId(e.target.value); setPage(1) }}
            className="px-3 py-2 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none"
          >
            <option value="">Все классы</option>
            {classes.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <select
            value={clubId}
            onChange={(e) => { setClubId(e.target.value); setPage(1) }}
            className="px-3 py-2 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none"
          >
            <option value="">Все клубы</option>
            {clubs.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <select
            value={regionId}
            onChange={(e) => { setRegionId(e.target.value); setPage(1) }}
            className="px-3 py-2 bg-surface border border-border rounded-lg text-text text-sm focus:outline-none"
          >
            <option value="">Все регионы</option>
            {regions.map((r) => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
          {hasFilters && (
            <button onClick={clearFilters} className="flex items-center gap-1 text-sm text-text-muted hover:text-danger cursor-pointer bg-transparent border-none">
              <X className="w-4 h-4" /> Сбросить
            </button>
          )}
        </div>
      )}

      <div className="bg-surface-light rounded-xl border border-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="px-4 py-3 text-text-muted font-medium">ФИО</th>
                <th className="px-4 py-3 text-text-muted font-medium hidden sm:table-cell">Пол</th>
                <th className="px-4 py-3 text-text-muted font-medium hidden md:table-cell">Возраст</th>
                <th className="px-4 py-3 text-text-muted font-medium">Вес</th>
                <th className="px-4 py-3 text-text-muted font-medium hidden lg:table-cell">Класс</th>
                <th className="px-4 py-3 text-text-muted font-medium hidden lg:table-cell">Клуб</th>
                <th className="px-4 py-3 text-text-muted font-medium hidden xl:table-cell">Регион</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="px-4 py-12 text-center text-text-muted">Загрузка...</td></tr>
              ) : participants.length === 0 ? (
                <tr><td colSpan={7} className="px-4 py-12 text-center text-text-muted">Участники не найдены</td></tr>
              ) : (
                participants.map((p) => (
                  <tr key={p.id} className="border-b border-border/50 hover:bg-surface-lighter/30 transition-colors">
                    <td className="px-4 py-3 font-medium">{p.fio}</td>
                    <td className="px-4 py-3 hidden sm:table-cell">
                      <span className={`text-xs px-2 py-1 rounded-full font-medium ${p.gender === 'Мужской' ? 'bg-male/10 text-male' : 'bg-female/10 text-female'}`}>
                        {p.gender === 'Мужской' ? 'М' : 'Ж'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-text-secondary hidden md:table-cell">{p.age_category_name}</td>
                    <td className="px-4 py-3 text-text-secondary">{p.weight}</td>
                    <td className="px-4 py-3 text-text-secondary hidden lg:table-cell">{p.class_name}</td>
                    <td className="px-4 py-3 text-text-secondary hidden lg:table-cell">{p.club_name}</td>
                    <td className="px-4 py-3 text-text-secondary hidden xl:table-cell">{p.region_name}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page <= 1}
            className="p-2 rounded-lg bg-surface-light border border-border disabled:opacity-30 cursor-pointer disabled:cursor-default text-text"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <span className="px-4 py-2 text-sm text-text-secondary">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage(Math.min(totalPages, page + 1))}
            disabled={page >= totalPages}
            className="p-2 rounded-lg bg-surface-light border border-border disabled:opacity-30 cursor-pointer disabled:cursor-default text-text"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      )}
    </div>
  )
}

import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { publicApi } from '../api'
import { Trophy, ChevronLeft } from 'lucide-react'

interface ApprovedBracket {
  class_name: string
  gender: string
  age_category_name: string
  weight_name: string
}

export default function BracketsPage() {
  const { id: competitionId } = useParams<{ id?: string }>()
  const [brackets, setBrackets] = useState<ApprovedBracket[]>([])
  const [selected, setSelected] = useState<ApprovedBracket | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    publicApi.getApprovedBrackets().then((r) => {
      setBrackets(r.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const grouped: Record<string, ApprovedBracket[]> = {}
  brackets.forEach((b) => {
    const key = `${b.gender} - ${b.age_category_name}`
    if (!grouped[key]) grouped[key] = []
    grouped[key].push(b)
  })

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
      <h1 className="text-2xl font-bold mb-6">Турнирные сетки</h1>

      {loading ? (
        <div className="text-center py-12 text-text-muted">Загрузка...</div>
      ) : brackets.length === 0 ? (
        <div className="text-center py-16">
          <Trophy className="w-16 h-16 mx-auto mb-4 text-text-muted" />
          <p className="text-text-muted text-lg">Утверждённых сеток пока нет</p>
          <p className="text-text-muted text-sm mt-2">Сетки появятся после утверждения администратором</p>
        </div>
      ) : (
        <div className="space-y-4">
          {Object.entries(grouped).map(([group, items]) => (
            <div key={group} className="bg-surface-light rounded-xl border border-border overflow-hidden">
              <div className="px-4 py-3 border-b border-border">
                <h3 className="font-semibold text-text">{group}</h3>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-px bg-border">
                {items.map((b, i) => (
                  <button
                    key={i}
                    onClick={() => setSelected(b)}
                    className={`bg-surface-light px-4 py-3 text-left cursor-pointer border-none hover:bg-surface-lighter/50 transition-colors ${
                      selected === b ? 'bg-primary/5 text-primary' : 'text-text'
                    }`}
                  >
                    <div className="font-medium text-sm">{b.class_name}</div>
                    <div className="text-text-muted text-xs mt-1">{b.weight_name} kg</div>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {selected && (
        <div className="mt-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold">
              {selected.class_name} - {selected.gender}, {selected.age_category_name}, {selected.weight_name} kg
            </h2>
            <button
              onClick={() => setSelected(null)}
              className="text-text-muted hover:text-text text-sm cursor-pointer bg-transparent border-none"
            >
              Закрыть
            </button>
          </div>
          <div className="bg-surface-light rounded-xl border border-border p-4 overflow-x-auto">
            <img
              src={publicApi.getBracketImage({
                class_name: selected.class_name,
                gender: selected.gender,
                age_category_name: selected.age_category_name,
                weight_name: selected.weight_name,
              })}
              alt="Турнирная сетка"
              className="max-w-full"
            />
          </div>
        </div>
      )}
    </div>
  )
}

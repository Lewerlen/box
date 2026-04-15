import { useState, useEffect } from 'react'
import { registrationApi } from '../api'
import { CheckCircle, ChevronRight, ChevronLeft, Loader2 } from 'lucide-react'

interface RefItem { id: number; name: string }

const STEPS = ['ФИО', 'Пол', 'Дата рождения', 'Вес. категория', 'Дисциплина', 'Разряд', 'Регион', 'Город', 'Клуб', 'Тренер', 'Подтверждение']

export default function RegistrationPage() {
  const [step, setStep] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')

  const [fio, setFio] = useState('')
  const [gender, setGender] = useState('')
  const [dob, setDob] = useState('')
  const [ageCategoryId, setAgeCategoryId] = useState<number | null>(null)
  const [ageCategoryName, setAgeCategoryName] = useState('')
  const [weightCategoryId, setWeightCategoryId] = useState<number | null>(null)
  const [weightCategoryName, setWeightCategoryName] = useState('')
  const [className, setClassName] = useState('')
  const [rankName, setRankName] = useState('')
  const [regionId, setRegionId] = useState<number | null>(null)
  const [regionName, setRegionName] = useState('')
  const [cityId, setCityId] = useState<number | null>(null)
  const [cityName, setCityName] = useState('')
  const [clubId, setClubId] = useState<number | null>(null)
  const [clubName, setClubName] = useState('')
  const [coachName, setCoachName] = useState('')
  const [manualCity, setManualCity] = useState('')
  const [manualClub, setManualClub] = useState('')
  const [manualCoach, setManualCoach] = useState('')

  const [weightCategories, setWeightCategories] = useState<RefItem[]>([])
  const [classes, setClasses] = useState<RefItem[]>([])
  const [ranks, setRanks] = useState<RefItem[]>([])
  const [regions, setRegions] = useState<RefItem[]>([])
  const [cities, setCities] = useState<RefItem[]>([])
  const [clubs, setClubs] = useState<RefItem[]>([])
  const [coaches, setCoaches] = useState<RefItem[]>([])

  useEffect(() => {
    if (step === 3 && ageCategoryId) {
      registrationApi.getWeightCategories(ageCategoryId).then((r) => setWeightCategories(r.data))
    }
    if (step === 4) registrationApi.getClasses().then((r) => setClasses(r.data))
    if (step === 5) registrationApi.getRanks().then((r) => setRanks(r.data))
    if (step === 6) registrationApi.getRegions().then((r) => setRegions(r.data))
    if (step === 7 && regionId) registrationApi.getCities(regionId).then((r) => setCities(r.data))
    if (step === 8 && cityId) registrationApi.getClubs(cityId).then((r) => setClubs(r.data))
    if (step === 9 && clubId) registrationApi.getCoaches(clubId).then((r) => setCoaches(r.data))
  }, [step, ageCategoryId, regionId, cityId, clubId])

  const handleDobSubmit = async () => {
    if (!dob || !gender) return
    try {
      const formatted = dob.split('-').length === 3 ? dob : ''
      if (!formatted) { setError('Введите дату в формате ГГГГ-ММ-ДД'); return }
      const res = await registrationApi.determineAgeCategory(formatted, gender)
      setAgeCategoryId(res.data.age_category.id)
      setAgeCategoryName(res.data.age_category.name)
      setError('')
      setStep(3)
    } catch {
      setError('Не удалось определить возрастную категорию')
    }
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    setError('')
    try {
      const finalCity = cityName || manualCity
      const finalClub = clubName || manualClub
      const finalCoach = coachName || manualCoach
      await registrationApi.submit({
        fio, gender, dob,
        age_category_id: ageCategoryId!,
        weight_category_id: weightCategoryId!,
        class_name: className,
        rank_name: rankName || null,
        region_name: regionName,
        city_name: finalCity,
        club_name: finalClub,
        coach_name: finalCoach,
      })
      setSuccess(true)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(err.response?.data?.detail || 'Ошибка при регистрации')
    }
    setSubmitting(false)
  }

  if (success) {
    return (
      <div className="max-w-xl mx-auto px-4 py-16 text-center">
        <CheckCircle className="w-16 h-16 mx-auto mb-4 text-success" />
        <h2 className="text-2xl font-bold mb-2">Регистрация завершена!</h2>
        <p className="text-text-secondary mb-6">Участник успешно зарегистрирован на турнир.</p>
        <button onClick={() => { setSuccess(false); setStep(0); setFio(''); setGender(''); setDob('') }} className="px-6 py-3 bg-primary text-white rounded-xl font-medium cursor-pointer border-none">
          Зарегистрировать ещё
        </button>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-2">Регистрация участника</h1>
      <p className="text-text-muted text-sm mb-8">Шаг {step + 1} из {STEPS.length}: {STEPS[step]}</p>

      <div className="flex gap-1 mb-8">
        {STEPS.map((_, i) => (
          <div key={i} className={`h-1 flex-1 rounded-full ${i <= step ? 'bg-primary' : 'bg-surface-lighter'}`} />
        ))}
      </div>

      {error && (
        <div className="bg-danger/10 border border-danger/30 text-danger rounded-lg px-4 py-3 mb-4 text-sm">{error}</div>
      )}

      <div className="bg-surface-light rounded-xl border border-border p-6">
        {step === 0 && (
          <div>
            <label className="block text-sm text-text-secondary mb-2">Фамилия Имя Отчество</label>
            <input value={fio} onChange={(e) => setFio(e.target.value)} placeholder="Иванов Иван Иванович"
              className="w-full px-4 py-3 bg-surface border border-border rounded-lg text-text placeholder:text-text-muted focus:outline-none focus:border-primary/50" />
            <button onClick={() => fio.trim().split(' ').length >= 2 ? setStep(1) : setError('Введите минимум Фамилию и Имя')}
              className="mt-4 w-full py-3 bg-primary hover:bg-primary-dark text-white rounded-lg font-medium cursor-pointer border-none transition-colors">
              <span className="flex items-center justify-center gap-2">Далее <ChevronRight className="w-4 h-4" /></span>
            </button>
          </div>
        )}

        {step === 1 && (
          <div>
            <label className="block text-sm text-text-secondary mb-3">Выберите пол</label>
            <div className="grid grid-cols-2 gap-3">
              {['Мужской', 'Женский'].map((g) => (
                <button key={g} onClick={() => { setGender(g); setStep(2) }}
                  className={`py-4 rounded-lg border text-center font-medium cursor-pointer transition-all ${gender === g ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-surface hover:border-primary/30 text-text'}`}>
                  {g}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 2 && (
          <div>
            <label className="block text-sm text-text-secondary mb-2">Дата рождения</label>
            <input type="date" value={dob} onChange={(e) => setDob(e.target.value)}
              className="w-full px-4 py-3 bg-surface border border-border rounded-lg text-text focus:outline-none focus:border-primary/50" />
            {ageCategoryName && <p className="mt-2 text-sm text-success">Категория: {ageCategoryName}</p>}
            <button onClick={handleDobSubmit}
              className="mt-4 w-full py-3 bg-primary hover:bg-primary-dark text-white rounded-lg font-medium cursor-pointer border-none transition-colors">
              <span className="flex items-center justify-center gap-2">Далее <ChevronRight className="w-4 h-4" /></span>
            </button>
          </div>
        )}

        {step === 3 && (
          <div>
            <label className="block text-sm text-text-secondary mb-3">Весовая категория (категория: {ageCategoryName})</label>
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 max-h-64 overflow-y-auto">
              {weightCategories.map((w) => (
                <button key={w.id} onClick={() => { setWeightCategoryId(w.id); setWeightCategoryName(w.name); setStep(4) }}
                  className={`py-3 px-2 rounded-lg border text-sm font-medium cursor-pointer transition-all ${weightCategoryId === w.id ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-surface hover:border-primary/30 text-text'}`}>
                  {w.name}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 4 && (
          <div>
            <label className="block text-sm text-text-secondary mb-3">Дисциплина</label>
            <div className="space-y-2">
              {classes.map((c) => (
                <button key={c.id} onClick={() => { setClassName(c.name); setStep(5) }}
                  className={`w-full py-3 px-4 rounded-lg border text-left font-medium cursor-pointer transition-all ${className === c.name ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-surface hover:border-primary/30 text-text'}`}>
                  {c.name}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 5 && (
          <div>
            <label className="block text-sm text-text-secondary mb-3">Разряд (необязательно)</label>
            <div className="grid grid-cols-2 gap-2">
              {ranks.map((r) => (
                <button key={r.id} onClick={() => { setRankName(r.name); setStep(6) }}
                  className={`py-3 px-4 rounded-lg border text-sm font-medium cursor-pointer transition-all ${rankName === r.name ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-surface hover:border-primary/30 text-text'}`}>
                  {r.name}
                </button>
              ))}
            </div>
            <button onClick={() => { setRankName(''); setStep(6) }}
              className="mt-3 w-full py-3 bg-surface-lighter hover:bg-surface-lighter/70 text-text-secondary rounded-lg font-medium cursor-pointer border-none transition-colors">
              Пропустить
            </button>
          </div>
        )}

        {step === 6 && (
          <div>
            <label className="block text-sm text-text-secondary mb-3">Регион</label>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {regions.map((r) => (
                <button key={r.id} onClick={() => { setRegionId(r.id); setRegionName(r.name); setCityId(null); setCityName(''); setStep(7) }}
                  className={`w-full py-3 px-4 rounded-lg border text-left text-sm font-medium cursor-pointer transition-all ${regionId === r.id ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-surface hover:border-primary/30 text-text'}`}>
                  {r.name}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 7 && (
          <div>
            <label className="block text-sm text-text-secondary mb-3">Город / населённый пункт</label>
            {cities.length > 0 && (
              <div className="space-y-2 max-h-48 overflow-y-auto mb-3">
                {cities.map((c) => (
                  <button key={c.id} onClick={() => { setCityId(c.id); setCityName(c.name); setManualCity(''); setStep(8) }}
                    className={`w-full py-3 px-4 rounded-lg border text-left text-sm font-medium cursor-pointer transition-all ${cityId === c.id ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-surface hover:border-primary/30 text-text'}`}>
                    {c.name}
                  </button>
                ))}
              </div>
            )}
            <div className="border-t border-border pt-3">
              <label className="block text-xs text-text-muted mb-1">Или введите вручную:</label>
              <input value={manualCity} onChange={(e) => setManualCity(e.target.value)} placeholder="Название города"
                className="w-full px-4 py-3 bg-surface border border-border rounded-lg text-text text-sm placeholder:text-text-muted focus:outline-none focus:border-primary/50" />
              {manualCity && (
                <button onClick={() => { setCityName(manualCity); setCityId(null); setStep(8) }}
                  className="mt-2 w-full py-2 bg-primary text-white rounded-lg text-sm font-medium cursor-pointer border-none">Далее</button>
              )}
            </div>
          </div>
        )}

        {step === 8 && (
          <div>
            <label className="block text-sm text-text-secondary mb-3">Клуб</label>
            {clubs.length > 0 && (
              <div className="space-y-2 max-h-48 overflow-y-auto mb-3">
                {clubs.map((c) => (
                  <button key={c.id} onClick={() => { setClubId(c.id); setClubName(c.name); setManualClub(''); setStep(9) }}
                    className={`w-full py-3 px-4 rounded-lg border text-left text-sm font-medium cursor-pointer transition-all ${clubId === c.id ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-surface hover:border-primary/30 text-text'}`}>
                    {c.name}
                  </button>
                ))}
              </div>
            )}
            <div className="border-t border-border pt-3">
              <label className="block text-xs text-text-muted mb-1">Или введите вручную:</label>
              <input value={manualClub} onChange={(e) => setManualClub(e.target.value)} placeholder="Название клуба"
                className="w-full px-4 py-3 bg-surface border border-border rounded-lg text-text text-sm placeholder:text-text-muted focus:outline-none focus:border-primary/50" />
              {manualClub && (
                <button onClick={() => { setClubName(manualClub); setClubId(null); setStep(9) }}
                  className="mt-2 w-full py-2 bg-primary text-white rounded-lg text-sm font-medium cursor-pointer border-none">Далее</button>
              )}
            </div>
          </div>
        )}

        {step === 9 && (
          <div>
            <label className="block text-sm text-text-secondary mb-3">ФИО тренера</label>
            {coaches.length > 0 && (
              <div className="space-y-2 max-h-48 overflow-y-auto mb-3">
                {coaches.map((c) => (
                  <button key={c.id} onClick={() => { setCoachName(c.name); setManualCoach(''); setStep(10) }}
                    className={`w-full py-3 px-4 rounded-lg border text-left text-sm font-medium cursor-pointer transition-all ${coachName === c.name ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-surface hover:border-primary/30 text-text'}`}>
                    {c.name}
                  </button>
                ))}
              </div>
            )}
            <div className="border-t border-border pt-3">
              <label className="block text-xs text-text-muted mb-1">Или введите вручную:</label>
              <input value={manualCoach} onChange={(e) => setManualCoach(e.target.value)} placeholder="ФИО тренера"
                className="w-full px-4 py-3 bg-surface border border-border rounded-lg text-text text-sm placeholder:text-text-muted focus:outline-none focus:border-primary/50" />
              {manualCoach && (
                <button onClick={() => { setCoachName(manualCoach); setStep(10) }}
                  className="mt-2 w-full py-2 bg-primary text-white rounded-lg text-sm font-medium cursor-pointer border-none">Далее</button>
              )}
            </div>
          </div>
        )}

        {step === 10 && (
          <div>
            <h3 className="text-lg font-semibold mb-4">Проверьте данные</h3>
            <div className="space-y-2 text-sm">
              {[
                ['ФИО', fio], ['Пол', gender], ['Дата рождения', dob], ['Возр. категория', ageCategoryName],
                ['Весовая кат.', weightCategoryName], ['Дисциплина', className], ['Разряд', rankName || 'Не указан'],
                ['Регион', regionName], ['Город', cityName || manualCity], ['Клуб', clubName || manualClub], ['Тренер', coachName || manualCoach],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between py-2 border-b border-border/50">
                  <span className="text-text-muted">{label}</span>
                  <span className="text-text font-medium">{value}</span>
                </div>
              ))}
            </div>
            <button onClick={handleSubmit} disabled={submitting}
              className="mt-6 w-full py-3 bg-success hover:bg-success/90 text-white rounded-lg font-medium cursor-pointer border-none transition-colors disabled:opacity-50">
              {submitting ? (
                <span className="flex items-center justify-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Сохранение...</span>
              ) : (
                <span className="flex items-center justify-center gap-2"><CheckCircle className="w-4 h-4" /> Зарегистрировать</span>
              )}
            </button>
          </div>
        )}
      </div>

      {step > 0 && step < 10 && (
        <button onClick={() => setStep(step - 1)}
          className="mt-4 flex items-center gap-2 text-text-muted hover:text-text text-sm cursor-pointer bg-transparent border-none transition-colors">
          <ChevronLeft className="w-4 h-4" /> Назад
        </button>
      )}
    </div>
  )
}

import { useState, useEffect, useRef } from 'react'
import { registrationApi } from '../api'
import { CheckCircle, ChevronLeft, ChevronDown, Loader2, X, SkipForward } from 'lucide-react'

interface CustomSelectProps {
  value: number
  onChange: (val: number) => void
  options: { value: number; label: string }[]
}

function CustomSelect({ value, onChange, options }: CustomSelectProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    if (open) document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  useEffect(() => {
    if (open && listRef.current) {
      const selected = listRef.current.querySelector('[data-selected="true"]') as HTMLElement
      if (selected) selected.scrollIntoView({ block: 'center' })
    }
  }, [open])

  const selected = options.find(o => o.value === value)

  return (
    <div ref={ref} className="relative">
      <button type="button" onClick={() => setOpen(o => !o)}
        className="w-full px-3 py-3 bg-surface-light border border-border rounded-lg text-text flex items-center justify-between focus:outline-none focus:border-primary/50 cursor-pointer transition-colors hover:border-primary/40">
        <span className="font-medium">{selected?.label ?? value}</span>
        <ChevronDown className={`w-4 h-4 text-text-muted transition-transform duration-150 ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div ref={listRef}
          className="absolute z-50 w-full mt-1 bg-surface border border-border rounded-lg shadow-xl overflow-y-auto"
          style={{ maxHeight: '320px', scrollbarWidth: 'thin', scrollbarColor: 'var(--color-border) var(--color-surface-light)' }}>
          {options.map(o => (
            <button key={o.value} type="button" data-selected={o.value === value}
              onClick={() => { onChange(o.value); setOpen(false) }}
              className={`w-full px-4 py-2.5 text-left text-sm cursor-pointer border-none transition-colors ${o.value === value ? 'bg-primary/15 text-primary font-semibold' : 'bg-transparent text-text hover:bg-surface-lighter'}`}>
              {o.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

interface RefItem { id: number; name: string }

const STEP_LABELS: Record<number, string> = {
  1: 'ФИО',
  2: 'Пол',
  3: 'Дата рождения',
  4: 'Возрастная категория',
  5: 'Весовая категория',
  6: 'Класс',
  7: 'Разряд',
  8: 'Дата присвоения разряда',
  9: 'Номер приказа',
  10: 'Регион',
  11: 'Город',
  12: 'Клуб',
  13: 'Тренер',
  14: 'Подтверждение',
}

const TOTAL_STEPS = 14

const MONTHS = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']


function parseDateInput(input: string): { valid: boolean; iso: string; display: string } {
  const cleaned = input.trim().replace(/-/g, '.')
  const match = cleaned.match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/)
  if (!match) return { valid: false, iso: '', display: '' }
  const day = parseInt(match[1])
  const month = parseInt(match[2])
  const year = parseInt(match[3])
  const currentYear = new Date().getFullYear()
  if (day < 1 || day > 31) return { valid: false, iso: '', display: '' }
  if (month < 1 || month > 12) return { valid: false, iso: '', display: '' }
  if (year < currentYear - 100 || year > currentYear - 1) return { valid: false, iso: '', display: '' }
  const iso = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
  const display = `${String(day).padStart(2, '0')}.${String(month).padStart(2, '0')}.${year}`
  return { valid: true, iso, display }
}

export default function RegistrationPage() {
  const [step, setStep] = useState(1)
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [cancelled, setCancelled] = useState(false)

  const [fio, setFio] = useState('')
  const [gender, setGender] = useState('')
  const [dobDay, setDobDay] = useState(1)
  const [dobMonth, setDobMonth] = useState(1)
  const [dobYear, setDobYear] = useState(2000)
  const [dobIso, setDobIso] = useState('')
  const [dobDisplay, setDobDisplay] = useState('')
  const [ageCategoryId, setAgeCategoryId] = useState<number | null>(null)
  const [ageCategoryName, setAgeCategoryName] = useState('')
  const [weightCategoryId, setWeightCategoryId] = useState<number | null>(null)
  const [weightCategoryName, setWeightCategoryName] = useState('')
  const [className, setClassName] = useState('')
  const [rankName, setRankName] = useState('')
  const [rankDateInput, setRankDateInput] = useState('')
  const [rankDateIso, setRankDateIso] = useState('')
  const [rankDateDisplay, setRankDateDisplay] = useState('')
  const [orderNumber, setOrderNumber] = useState('')
  const [regionId, setRegionId] = useState<number | null>(null)
  const [regionName, setRegionName] = useState('')
  const [cityId, setCityId] = useState<number | null>(null)
  const [cityName, setCityName] = useState('')
  const [clubId, setClubId] = useState<number | null>(null)
  const [clubName, setClubName] = useState('')
  const [coachName, setCoachName] = useState('')

  const [manualRegion, setManualRegion] = useState('')
  const [manualCity, setManualCity] = useState('')
  const [manualClub, setManualClub] = useState('')
  const [manualCoach, setManualCoach] = useState('')
  const [manualMode, setManualMode] = useState<Record<string, boolean>>({})

  const [weightCategories, setWeightCategories] = useState<RefItem[]>([])
  const [classes, setClasses] = useState<RefItem[]>([])
  const [ranks, setRanks] = useState<RefItem[]>([])
  const [regions, setRegions] = useState<RefItem[]>([])
  const [cities, setCities] = useState<RefItem[]>([])
  const [clubs, setClubs] = useState<RefItem[]>([])
  const [coaches, setCoaches] = useState<RefItem[]>([])

  const [skippedSteps, setSkippedSteps] = useState<Set<number>>(new Set([4]))

  useEffect(() => {
    if (step === 5 && ageCategoryId) {
      registrationApi.getWeightCategories(ageCategoryId).then((r) => setWeightCategories(r.data))
    }
    if (step === 6) {
      registrationApi.getClasses().then((r) => {
        const active = r.data.filter((c: RefItem & { status?: boolean }) => c.status !== false)
        setClasses(active)
        if (active.length === 0) {
          setClassName('')
          const next = new Set(skippedSteps)
          next.add(6)
          next.add(7)
          next.add(8)
          next.add(9)
          setSkippedSteps(next)
          setStep(10)
        }
      })
    }
    if (step === 7) {
      registrationApi.getRanks().then((r) => {
        const active = r.data.filter((rank: RefItem & { status?: boolean }) => rank.status !== false)
        setRanks(active)
      })
    }
    if (step === 10) registrationApi.getRegions().then((r) => setRegions(r.data))
    if (step === 11 && regionId) registrationApi.getCities(regionId).then((r) => setCities(r.data))
    if (step === 12 && cityId) registrationApi.getClubs(cityId).then((r) => setClubs(r.data))
    if (step === 13 && clubId) registrationApi.getCoaches(clubId).then((r) => setCoaches(r.data))
  }, [step, ageCategoryId, regionId, cityId, clubId])

  const handleDobSubmit = async () => {
    const iso = `${dobYear}-${String(dobMonth).padStart(2, '0')}-${String(dobDay).padStart(2, '0')}`
    const display = `${String(dobDay).padStart(2, '0')}.${String(dobMonth).padStart(2, '0')}.${dobYear}`
    setDobIso(iso)
    setDobDisplay(display)
    if (!gender) { setError('Пол не выбран'); return }
    try {
      const res = await registrationApi.determineAgeCategory(iso, gender)
      setAgeCategoryId(res.data.age_category.id)
      setAgeCategoryName(res.data.age_category.name)
      setError('')
      const next = new Set(skippedSteps)
      next.add(4)
      setSkippedSteps(next)
      setStep(5)
    } catch {
      setError('Не удалось определить возрастную категорию для данной даты рождения')
    }
  }

  const handleRankDateSubmit = () => {
    if (!rankDateInput) { setError('Введите дату присвоения разряда'); return }
    const parsed = parseDateInput(rankDateInput)
    if (!parsed.valid) {
      setError('Неверная дата. Введите дату в формате ДД.ММ.ГГГГ или ДД-ММ-ГГГГ.')
      return
    }
    setRankDateIso(parsed.iso)
    setRankDateDisplay(parsed.display)
    setError('')
    setStep(9)
  }

  const goBack = () => {
    setError('')
    let prev = step - 1
    while (prev >= 1 && skippedSteps.has(prev)) prev--
    if (prev >= 1) setStep(prev)
  }

  const handleCancel = () => {
    setCancelled(true)
  }

  const resetForm = () => {
    setStep(1)
    setFio(''); setGender(''); setDobDay(1); setDobMonth(1); setDobYear(2000); setDobIso(''); setDobDisplay('')
    setAgeCategoryId(null); setAgeCategoryName(''); setWeightCategoryId(null); setWeightCategoryName('')
    setClassName(''); setRankName(''); setRankDateInput(''); setRankDateIso(''); setRankDateDisplay('')
    setOrderNumber(''); setRegionId(null); setRegionName(''); setCityId(null); setCityName('')
    setClubId(null); setClubName(''); setCoachName('')
    setManualRegion(''); setManualCity(''); setManualClub(''); setManualCoach('')
    setManualMode({}); setSkippedSteps(new Set([4]))
    setError(''); setSuccess(null); setCancelled(false); setSubmitting(false)
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    setError('')
    try {
      const finalRegion = regionName || manualRegion
      const finalCity = cityName || manualCity
      const finalClub = clubName || manualClub
      const finalCoach = coachName || manualCoach
      const res = await registrationApi.submit({
        fio, gender, dob: dobIso,
        age_category_id: ageCategoryId!,
        weight_category_id: weightCategoryId!,
        class_name: className,
        rank_name: rankName || null,
        rank_assigned_on: rankDateIso || null,
        order_number: orderNumber || null,
        region_name: finalRegion,
        city_name: finalCity,
        club_name: finalClub,
        coach_name: finalCoach,
      })
      const status = res.data.status
      if (status === 'created') {
        setSuccess(`Добавлен участник: ${fio}`)
      } else {
        setSuccess(`Обновлён участник: ${fio}`)
      }
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(err.response?.data?.detail || 'Ошибка при сохранении')
    }
    setSubmitting(false)
  }

  if (cancelled) {
    return (
      <div className="max-w-xl mx-auto px-4 py-16 text-center">
        <X className="w-16 h-16 mx-auto mb-4 text-text-muted" />
        <h2 className="text-2xl font-bold mb-2 text-text">Добавление отменено.</h2>
        <button onClick={resetForm} className="mt-6 px-6 py-3 bg-primary text-white rounded-xl font-medium cursor-pointer border-none">
          Начать заново
        </button>
      </div>
    )
  }

  if (success) {
    return (
      <div className="max-w-xl mx-auto px-4 py-16 text-center">
        <CheckCircle className="w-16 h-16 mx-auto mb-4 text-success" />
        <h2 className="text-xl font-bold mb-2 text-text">{success}</h2>
        <button onClick={resetForm} className="mt-6 px-6 py-3 bg-primary text-white rounded-xl font-medium cursor-pointer border-none">
          Зарегистрировать ещё
        </button>
      </div>
    )
  }

  const activeSteps = Array.from({ length: TOTAL_STEPS }, (_, i) => i + 1).filter(s => !skippedSteps.has(s))
  const progressIndex = activeSteps.indexOf(step)
  const progressTotal = activeSteps.length

  const finalRegion = regionName || manualRegion
  const finalCity = cityName || manualCity
  const finalClub = clubName || manualClub
  const finalCoach = coachName || manualCoach

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-2 text-text">Регистрация участника</h1>
      <p className="text-text-muted text-sm mb-6">
        Шаг {progressIndex + 1} из {progressTotal}: {STEP_LABELS[step]}
      </p>

      <div className="flex gap-1 mb-6">
        {activeSteps.map((s, i) => (
          <div key={s} className={`h-1.5 flex-1 rounded-full transition-colors ${i <= progressIndex ? 'bg-primary' : 'bg-surface-lighter'}`} />
        ))}
      </div>

      {error && (
        <div className="bg-danger/10 border border-danger/30 text-danger rounded-lg px-4 py-3 mb-4 text-sm">{error}</div>
      )}

      <div className="bg-surface rounded-xl border border-border-light shadow-sm overflow-hidden">
        <div className="p-6">

        {step === 1 && (
          <div>
            <label className="block text-sm text-text-secondary mb-2">Фамилия Имя Отчество</label>
            <input value={fio} onChange={(e) => setFio(e.target.value)} placeholder="Иванов Иван Иванович"
              className="w-full px-4 py-3 bg-surface-light border border-border rounded-lg text-text placeholder:text-text-muted focus:outline-none focus:border-primary/50"
              onKeyDown={(e) => { if (e.key === 'Enter') { if (fio.trim().split(' ').length >= 2) { setError(''); setStep(2) } else { setError('Введите минимум Фамилию и Имя') } } }}
            />
            <button onClick={() => fio.trim().split(' ').length >= 2 ? (setError(''), setStep(2)) : setError('Введите минимум Фамилию и Имя')}
              className="mt-4 w-full py-3 bg-primary hover:bg-primary-dark text-white rounded-lg font-medium cursor-pointer border-none transition-colors">
              Далее
            </button>
          </div>
        )}

        {step === 2 && (
          <div>
            <label className="block text-sm text-text-secondary mb-3">Выберите пол</label>
            <div className="grid grid-cols-2 gap-3">
              {[{ value: 'Мужской', label: 'Мужской' }, { value: 'Женский', label: 'Женский' }].map((g) => (
                <button key={g.value} onClick={() => { setGender(g.value); setStep(3) }}
                  className={`py-4 rounded-lg border text-center font-medium cursor-pointer transition-all ${gender === g.value ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-surface-light hover:border-primary/30 text-text'}`}>
                  {g.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 3 && (
          <div>
            <label className="block text-sm text-text-secondary mb-4">Дата рождения</label>
            <div className="grid grid-cols-3 gap-3 mb-6">
              <div>
                <label className="block text-xs text-text-muted mb-1.5">День</label>
                <CustomSelect value={dobDay} onChange={setDobDay}
                  options={Array.from({ length: 31 }, (_, i) => ({ value: i + 1, label: String(i + 1) }))} />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1.5">Месяц</label>
                <CustomSelect value={dobMonth} onChange={setDobMonth}
                  options={MONTHS.map((m, i) => ({ value: i + 1, label: m }))} />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1.5">Год</label>
                <CustomSelect value={dobYear} onChange={setDobYear}
                  options={Array.from({ length: 55 }, (_, i) => ({ value: 2024 - i, label: String(2024 - i) }))} />
              </div>
            </div>
            {ageCategoryName && (
              <div className="mb-4 flex items-center gap-2 px-4 py-2.5 bg-primary/10 border border-primary/20 rounded-lg">
                <span className="text-xs text-text-muted">Возрастная категория:</span>
                <span className="font-semibold text-primary">{ageCategoryName}</span>
              </div>
            )}
            <button onClick={handleDobSubmit}
              className="w-full py-3 bg-primary hover:bg-primary-dark text-white rounded-lg font-medium cursor-pointer border-none transition-colors">
              Далее
            </button>
          </div>
        )}

        {step === 5 && (
          <div>
            <label className="block text-sm text-text-secondary mb-3">Весовая категория</label>
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 max-h-64 overflow-y-auto">
              {weightCategories.map((w) => (
                <button key={w.id} onClick={() => { setWeightCategoryId(w.id); setWeightCategoryName(w.name); setStep(6) }}
                  className={`py-3 px-2 rounded-lg border text-sm font-medium cursor-pointer transition-all ${weightCategoryId === w.id ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-surface-light hover:border-primary/30 text-text'}`}>
                  {w.name}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 6 && (
          <div>
            <label className="block text-sm text-text-secondary mb-3">Класс</label>
            <div className="space-y-2">
              {classes.map((c) => (
                <button key={c.id} onClick={() => {
                  setClassName(c.name)
                  const isA = c.name.toLowerCase().includes('а') && c.name.toLowerCase().includes('опытн')
                  if (!isA) {
                    setRankName(''); setRankDateInput(''); setRankDateIso(''); setRankDateDisplay(''); setOrderNumber('')
                    const next = new Set(skippedSteps)
                    next.add(7); next.add(8); next.add(9)
                    setSkippedSteps(next)
                    setStep(10)
                  } else {
                    const next = new Set(skippedSteps)
                    next.delete(7); next.delete(8); next.delete(9)
                    setSkippedSteps(next)
                    setStep(7)
                  }
                }}
                  className={`w-full py-3 px-4 rounded-lg border text-left font-medium cursor-pointer transition-all ${className === c.name ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-surface-light hover:border-primary/30 text-text'}`}>
                  {c.name}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 7 && (
          <div>
            <label className="block text-sm text-text-secondary mb-3">Разряд (если есть)</label>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {ranks.map((r) => (
                <button key={r.id} onClick={() => { setRankName(r.name); setError(''); setStep(8) }}
                  className={`w-full py-3 px-4 rounded-lg border text-left text-sm font-medium cursor-pointer transition-all ${rankName === r.name ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-surface-light hover:border-primary/30 text-text'}`}>
                  {r.name}
                </button>
              ))}
            </div>
            <button onClick={() => {
              setRankName(''); setRankDateInput(''); setRankDateIso(''); setRankDateDisplay(''); setOrderNumber('')
              const next = new Set(skippedSteps)
              next.add(8); next.add(9)
              setSkippedSteps(next)
              setStep(10)
            }}
              className="mt-3 w-full py-3 bg-surface-lighter hover:bg-surface-lighter/80 text-text-secondary rounded-lg font-medium cursor-pointer border-none transition-colors flex items-center justify-center gap-2">
              <SkipForward className="w-4 h-4" /> Пропустить
            </button>
          </div>
        )}

        {step === 8 && (
          <div>
            <label className="block text-sm text-text-secondary mb-2">Дата присвоения разряда (ДД.ММ.ГГГГ)</label>
            <input value={rankDateInput} onChange={(e) => setRankDateInput(e.target.value)} placeholder="01.01.2023"
              className="w-full px-4 py-3 bg-surface-light border border-border rounded-lg text-text placeholder:text-text-muted focus:outline-none focus:border-primary/50"
              onKeyDown={(e) => { if (e.key === 'Enter') handleRankDateSubmit() }}
            />
            <button onClick={handleRankDateSubmit}
              className="mt-4 w-full py-3 bg-primary hover:bg-primary-dark text-white rounded-lg font-medium cursor-pointer border-none transition-colors">
              Далее
            </button>
          </div>
        )}

        {step === 9 && (
          <div>
            <label className="block text-sm text-text-secondary mb-2">Номер приказа (без знака №, только номер)</label>
            <input value={orderNumber} onChange={(e) => setOrderNumber(e.target.value)} placeholder="12345"
              className="w-full px-4 py-3 bg-surface-light border border-border rounded-lg text-text placeholder:text-text-muted focus:outline-none focus:border-primary/50"
              onKeyDown={(e) => { if (e.key === 'Enter' && orderNumber.trim()) { setError(''); setStep(10) } }}
            />
            <button onClick={() => { if (orderNumber.trim()) { setError(''); setStep(10) } else { setError('Введите номер приказа') } }}
              className="mt-4 w-full py-3 bg-primary hover:bg-primary-dark text-white rounded-lg font-medium cursor-pointer border-none transition-colors">
              Далее
            </button>
          </div>
        )}

        {step === 10 && (
          <div>
            <label className="block text-sm text-text-secondary mb-3">
              {manualMode.region ? 'Введите Область/республику/край:' : 'Регион'}
            </label>
            {!manualMode.region ? (
              <>
                <div className="space-y-2 max-h-64 overflow-y-auto mb-3">
                  {regions.map((r) => (
                    <button key={r.id} onClick={() => {
                      setRegionId(r.id); setRegionName(r.name); setManualRegion('')
                      setCityId(null); setCityName(''); setManualCity('')
                      setClubId(null); setClubName(''); setManualClub('')
                      setCoachName(''); setManualCoach('')
                      setStep(11)
                    }}
                      className={`w-full py-3 px-4 rounded-lg border text-left text-sm font-medium cursor-pointer transition-all ${regionId === r.id ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-surface-light hover:border-primary/30 text-text'}`}>
                      {r.name}
                    </button>
                  ))}
                </div>
                <button onClick={() => setManualMode({ ...manualMode, region: true })}
                  className="w-full py-2.5 bg-surface-lighter hover:bg-surface-lighter/80 text-text-secondary rounded-lg text-sm font-medium cursor-pointer border-none transition-colors">
                  Ввести новый вручную
                </button>
              </>
            ) : (
              <>
                <input value={manualRegion} onChange={(e) => setManualRegion(e.target.value)} placeholder="Название региона"
                  className="w-full px-4 py-3 bg-surface-light border border-border rounded-lg text-text placeholder:text-text-muted focus:outline-none focus:border-primary/50"
                  onKeyDown={(e) => { if (e.key === 'Enter' && manualRegion.trim()) {
                    setRegionName(''); setRegionId(null); setCityId(null); setCityName(''); setManualCity('')
                    setClubId(null); setClubName(''); setManualClub(''); setCoachName(''); setManualCoach('')
                    setError(''); setStep(11)
                  }}}
                />
                {manualRegion.trim() && (
                  <button onClick={() => {
                    setRegionName(''); setRegionId(null); setCityId(null); setCityName(''); setManualCity('')
                    setClubId(null); setClubName(''); setManualClub(''); setCoachName(''); setManualCoach('')
                    setError(''); setStep(11)
                  }}
                    className="mt-3 w-full py-3 bg-primary hover:bg-primary-dark text-white rounded-lg font-medium cursor-pointer border-none transition-colors">
                    Далее
                  </button>
                )}
                <button onClick={() => { setManualMode({ ...manualMode, region: false }); setManualRegion('') }}
                  className="mt-2 w-full py-2.5 bg-surface-lighter hover:bg-surface-lighter/80 text-text-secondary rounded-lg text-sm font-medium cursor-pointer border-none transition-colors">
                  Вернуться к списку регионов
                </button>
              </>
            )}
          </div>
        )}

        {step === 11 && (
          <div>
            <label className="block text-sm text-text-secondary mb-3">
              {(manualMode.city || !regionId) ? 'Введите Город/населённый пункт:' : 'Город/населённый пункт'}
            </label>
            {regionId && !manualMode.city ? (
              <>
                {cities.length > 0 && (
                  <div className="space-y-2 max-h-48 overflow-y-auto mb-3">
                    {cities.map((c) => (
                      <button key={c.id} onClick={() => {
                        setCityId(c.id); setCityName(c.name); setManualCity('')
                        setClubId(null); setClubName(''); setManualClub('')
                        setCoachName(''); setManualCoach('')
                        setStep(12)
                      }}
                        className={`w-full py-3 px-4 rounded-lg border text-left text-sm font-medium cursor-pointer transition-all ${cityId === c.id ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-surface-light hover:border-primary/30 text-text'}`}>
                        {c.name}
                      </button>
                    ))}
                  </div>
                )}
                <button onClick={() => setManualMode({ ...manualMode, city: true })}
                  className="w-full py-2.5 bg-surface-lighter hover:bg-surface-lighter/80 text-text-secondary rounded-lg text-sm font-medium cursor-pointer border-none transition-colors">
                  Ввести новый вручную
                </button>
              </>
            ) : (
              <>
                <input value={manualCity} onChange={(e) => setManualCity(e.target.value)} placeholder="Название города"
                  className="w-full px-4 py-3 bg-surface-light border border-border rounded-lg text-text placeholder:text-text-muted focus:outline-none focus:border-primary/50"
                  onKeyDown={(e) => { if (e.key === 'Enter' && manualCity.trim()) {
                    setCityName(''); setCityId(null); setClubId(null); setClubName(''); setManualClub('')
                    setCoachName(''); setManualCoach(''); setError(''); setStep(12)
                  }}}
                />
                {manualCity.trim() && (
                  <button onClick={() => {
                    setCityName(''); setCityId(null); setClubId(null); setClubName(''); setManualClub('')
                    setCoachName(''); setManualCoach(''); setError(''); setStep(12)
                  }}
                    className="mt-3 w-full py-3 bg-primary hover:bg-primary-dark text-white rounded-lg font-medium cursor-pointer border-none transition-colors">
                    Далее
                  </button>
                )}
                {regionId && (
                  <button onClick={() => { setManualMode({ ...manualMode, city: false }); setManualCity('') }}
                    className="mt-2 w-full py-2.5 bg-surface-lighter hover:bg-surface-lighter/80 text-text-secondary rounded-lg text-sm font-medium cursor-pointer border-none transition-colors">
                    Вернуться к списку городов
                  </button>
                )}
              </>
            )}
          </div>
        )}

        {step === 12 && (
          <div>
            <label className="block text-sm text-text-secondary mb-3">
              {(manualMode.club || !cityId) ? 'Введите название Клуба:' : 'Клуб'}
            </label>
            {cityId && !manualMode.club ? (
              <>
                {clubs.length > 0 && (
                  <div className="space-y-2 max-h-48 overflow-y-auto mb-3">
                    {clubs.map((c) => (
                      <button key={c.id} onClick={() => {
                        setClubId(c.id); setClubName(c.name); setManualClub('')
                        setCoachName(''); setManualCoach('')
                        setStep(13)
                      }}
                        className={`w-full py-3 px-4 rounded-lg border text-left text-sm font-medium cursor-pointer transition-all ${clubId === c.id ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-surface-light hover:border-primary/30 text-text'}`}>
                        {c.name}
                      </button>
                    ))}
                  </div>
                )}
                <button onClick={() => setManualMode({ ...manualMode, club: true })}
                  className="w-full py-2.5 bg-surface-lighter hover:bg-surface-lighter/80 text-text-secondary rounded-lg text-sm font-medium cursor-pointer border-none transition-colors">
                  Ввести новый вручную
                </button>
              </>
            ) : (
              <>
                <input value={manualClub} onChange={(e) => setManualClub(e.target.value)} placeholder="Название клуба"
                  className="w-full px-4 py-3 bg-surface-light border border-border rounded-lg text-text placeholder:text-text-muted focus:outline-none focus:border-primary/50"
                  onKeyDown={(e) => { if (e.key === 'Enter' && manualClub.trim()) {
                    setClubName(''); setClubId(null); setCoachName(''); setManualCoach(''); setError(''); setStep(13)
                  }}}
                />
                {manualClub.trim() && (
                  <button onClick={() => {
                    setClubName(''); setClubId(null); setCoachName(''); setManualCoach(''); setError(''); setStep(13)
                  }}
                    className="mt-3 w-full py-3 bg-primary hover:bg-primary-dark text-white rounded-lg font-medium cursor-pointer border-none transition-colors">
                    Далее
                  </button>
                )}
                {cityId && (
                  <button onClick={() => { setManualMode({ ...manualMode, club: false }); setManualClub('') }}
                    className="mt-2 w-full py-2.5 bg-surface-lighter hover:bg-surface-lighter/80 text-text-secondary rounded-lg text-sm font-medium cursor-pointer border-none transition-colors">
                    Вернуться к списку клубов
                  </button>
                )}
              </>
            )}
          </div>
        )}

        {step === 13 && (
          <div>
            <label className="block text-sm text-text-secondary mb-3">
              {(manualMode.coach || !clubId || coaches.length === 0) ? 'Введите Тренера:' : 'Тренер'}
            </label>
            {clubId && coaches.length > 0 && !manualMode.coach ? (
              <>
                <div className="space-y-2 max-h-48 overflow-y-auto mb-3">
                  {coaches.map((c) => (
                    <button key={c.id} onClick={() => { setCoachName(c.name); setManualCoach(''); setStep(14) }}
                      className={`w-full py-3 px-4 rounded-lg border text-left text-sm font-medium cursor-pointer transition-all ${coachName === c.name ? 'border-primary bg-primary/10 text-primary' : 'border-border bg-surface-light hover:border-primary/30 text-text'}`}>
                      {c.name}
                    </button>
                  ))}
                </div>
                <button onClick={() => setManualMode({ ...manualMode, coach: true })}
                  className="w-full py-2.5 bg-surface-lighter hover:bg-surface-lighter/80 text-text-secondary rounded-lg text-sm font-medium cursor-pointer border-none transition-colors">
                  Ввести тренера вручную
                </button>
              </>
            ) : (
              <>
                <input value={manualCoach} onChange={(e) => setManualCoach(e.target.value)} placeholder="ФИО тренера"
                  className="w-full px-4 py-3 bg-surface-light border border-border rounded-lg text-text placeholder:text-text-muted focus:outline-none focus:border-primary/50"
                  onKeyDown={(e) => { if (e.key === 'Enter' && manualCoach.trim()) {
                    setCoachName(''); setError(''); setStep(14)
                  }}}
                />
                {manualCoach.trim() && (
                  <button onClick={() => { setCoachName(''); setError(''); setStep(14) }}
                    className="mt-3 w-full py-3 bg-primary hover:bg-primary-dark text-white rounded-lg font-medium cursor-pointer border-none transition-colors">
                    Далее
                  </button>
                )}
                {clubId && coaches.length > 0 && (
                  <button onClick={() => { setManualMode({ ...manualMode, coach: false }); setManualCoach('') }}
                    className="mt-2 w-full py-2.5 bg-surface-lighter hover:bg-surface-lighter/80 text-text-secondary rounded-lg text-sm font-medium cursor-pointer border-none transition-colors">
                    Вернуться к списку тренеров
                  </button>
                )}
              </>
            )}
          </div>
        )}

        {step === 14 && (
          <div>
            <h3 className="text-lg font-semibold mb-4 text-text">Проверьте данные перед сохранением:</h3>
            <div className="space-y-1 text-sm">
              {[
                ['ФИО', fio],
                ['Пол', gender],
                ['Дата рождения', dobDisplay],
                ['Возр. категория', ageCategoryName],
                ['Весовая кат.', weightCategoryName],
                ...(className ? [['Класс', className]] : []),
                ...(rankName ? [['Разряд', rankName]] : []),
                ...(rankDateDisplay ? [['Дата присв. разряда', rankDateDisplay]] : []),
                ...(orderNumber ? [['Номер приказа', orderNumber]] : []),
                ['Регион', finalRegion],
                ['Город', finalCity],
                ['Клуб', finalClub],
                ['Тренер', finalCoach],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between py-2.5 border-b border-border/50">
                  <span className="text-text-muted">{label}</span>
                  <span className="text-text font-medium text-right">{value}</span>
                </div>
              ))}
            </div>

            <div className="mt-6 space-y-2">
              <button onClick={handleSubmit} disabled={submitting}
                className="w-full py-3 bg-success hover:bg-success/90 text-white rounded-lg font-medium cursor-pointer border-none transition-colors disabled:opacity-50">
                {submitting ? (
                  <span className="flex items-center justify-center gap-2"><Loader2 className="w-4 h-4 animate-spin" /> Сохранение...</span>
                ) : (
                  <span className="flex items-center justify-center gap-2"><CheckCircle className="w-4 h-4" /> Сохранить</span>
                )}
              </button>
              <button onClick={() => setStep(13)}
                className="w-full py-3 bg-surface-lighter hover:bg-surface-lighter/80 text-text-secondary rounded-lg font-medium cursor-pointer border-none transition-colors">
                Вернуться к редактированию
              </button>
              <button onClick={handleCancel}
                className="w-full py-3 bg-danger/10 hover:bg-danger/20 text-danger rounded-lg font-medium cursor-pointer border-none transition-colors">
                Отменить
              </button>
            </div>
          </div>
        )}
        </div>

        {step > 1 && step < 14 && (
          <div className="border-t border-border-light px-6 py-3">
            <button onClick={goBack}
              className="flex items-center gap-1.5 text-text-muted hover:text-primary text-sm cursor-pointer bg-transparent border-none transition-colors font-medium">
              <ChevronLeft className="w-4 h-4" /> Назад
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

import { Clock } from 'lucide-react'

interface DeadlineBadgeProps {
  deadline: string | null
  className?: string
}

export function formatDeadlineDate(dateStr: string): string {
  const d = new Date(dateStr)
  const hasTime = dateStr.includes('T') && !dateStr.endsWith('T00:00:00') && !dateStr.endsWith('T00:00:00.000Z')
  if (hasTime) {
    return d.toLocaleString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
}

export function isDeadlineUrgent(dateStr: string): boolean {
  const deadline = new Date(dateStr)
  const now = new Date()
  const diffMs = deadline.getTime() - now.getTime()
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24))
  return diffDays >= 0 && diffDays <= 3
}

export function isDeadlinePassed(dateStr: string): boolean {
  const deadline = new Date(dateStr)
  return deadline < new Date()
}

export default function DeadlineBadge({ deadline, className = '' }: DeadlineBadgeProps) {
  if (!deadline) return null
  if (isDeadlinePassed(deadline)) return null

  const urgent = isDeadlineUrgent(deadline)

  return (
    <p className={`flex items-center gap-1.5 text-xs mt-1 ${urgent ? 'text-warning font-medium' : 'text-text-muted'} ${className}`}>
      <Clock className="w-3 h-3 shrink-0" />
      Регистрация до: {formatDeadlineDate(deadline)}
    </p>
  )
}

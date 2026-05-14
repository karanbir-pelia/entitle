import { ShieldCheck } from 'lucide-react'
import { getTranslations } from '../../utils/i18n.js'

export default function OfflineBadge({ language }) {
  const tx = getTranslations(language)
  return (
    <div className="inline-flex min-h-9 items-center gap-2 rounded-md bg-[var(--mint)] px-3 text-sm font-semibold text-[var(--green-dark)]">
      <ShieldCheck size={16} aria-hidden="true" />
      <span>{tx.offline}</span>
    </div>
  )
}

import { RotateCcw } from 'lucide-react'
import { getTranslations } from '../../utils/i18n.js'
import Button from '../Shared/Button.jsx'
import LanguageSelector from '../Shared/LanguageSelector.jsx'
import OfflineBadge from './OfflineBadge.jsx'

export default function Header({ language, onLanguageChange, onReset }) {
  const tx = getTranslations(language)
  return (
    <header className="sticky top-0 z-10 border-b border-[var(--line)] bg-white/95 backdrop-blur">
      <div className="mx-auto flex min-h-[72px] max-w-7xl items-center justify-between gap-3 px-4">
        <div className="min-w-0">
          <p className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--green)]">Entitle</p>
          <h1 className="truncate text-lg font-bold sm:text-2xl">{tx.nav}</h1>
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden md:block">
            <OfflineBadge language={language} />
          </div>
          <LanguageSelector value={language} onChange={onLanguageChange} />
          <Button variant="quiet" onClick={onReset} aria-label="Start over" title="Start over" className="px-3">
            <RotateCcw size={18} aria-hidden="true" />
          </Button>
        </div>
      </div>
    </header>
  )
}

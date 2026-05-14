import { formatCurrency } from '../../utils/formatting.js'
import OfflineBadge from './OfflineBadge.jsx'

export default function Sidebar({ activeTab, benefits, hasEstimatedValue, onTabChange, tabs, totalValue }) {
  return (
    <aside className="hidden border-r border-[var(--line)] bg-[#f7f8f4] lg:block">
      <div className="sticky top-[73px] flex h-[calc(100vh-73px)] flex-col p-4">
        <OfflineBadge />

        <nav className="mt-5 space-y-1">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => onTabChange(tab.id)}
                className={`flex h-11 w-full items-center gap-3 rounded-md px-3 text-left text-sm font-semibold transition ${
                  activeTab === tab.id
                    ? 'bg-[var(--green)] text-white'
                    : 'text-[var(--muted)] hover:bg-white hover:text-[var(--green-dark)]'
                }`}
              >
                <Icon size={18} aria-hidden="true" />
                <span>{tab.label}</span>
                {tab.id === 'results' && benefits.length > 0 && (
                  <span className="ml-auto rounded-full bg-white/20 px-2 py-0.5 text-xs">{benefits.length}</span>
                )}
              </button>
            )
          })}
        </nav>

        <div className="mt-6 rounded-md border border-[var(--line)] bg-white p-4">
          <p className="text-sm font-semibold text-[var(--muted)]">Estimated monthly value</p>
          <p className="mt-1 text-3xl font-bold text-[var(--green-dark)]">
            {benefits.length > 0 && !hasEstimatedValue ? 'Varies' : formatCurrency(totalValue)}
          </p>
          <p className="mt-2 text-sm leading-5 text-[var(--muted)]">
            Estimates are not final eligibility decisions. Local agencies make the official call.
          </p>
        </div>

        <div className="mt-auto text-sm leading-5 text-[var(--muted)]">
          Entitle does not submit applications or store accounts. For urgent local help, call 211.
        </div>
      </div>
    </aside>
  )
}

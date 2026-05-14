import { ChevronDown, ExternalLink } from 'lucide-react'
import { useState } from 'react'
import { compactProgramName, confidenceLabel, formatCurrency } from '../../utils/formatting.js'
import Button from '../Shared/Button.jsx'

export default function BenefitsCard({ benefit, onSelect }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <article className="rounded-md border border-[var(--line)] bg-white shadow-sm">
      <button
        type="button"
        onClick={() => setExpanded((current) => !current)}
        className="flex w-full items-start gap-4 p-4 text-left"
      >
        <div className="flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-bold text-[var(--ink)]">{compactProgramName(benefit.program_name)}</h3>
            <span className="rounded-full bg-[var(--mint)] px-2.5 py-1 text-xs font-bold text-[var(--green-dark)]">
              {confidenceLabel(benefit.confidence)}
            </span>
          </div>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{benefit.reason}</p>
        </div>

        <div className="flex shrink-0 flex-col items-end gap-1">
          {(() => {
            const period = benefit.value_period || 'monthly'
            const monthly = benefit.estimated_monthly_value_usd
            if (period === 'annual') {
              const annual = monthly != null ? monthly * 12 : null
              return (
                <>
                  <span className="text-lg font-bold text-[var(--green-dark)]">{formatCurrency(annual)}</span>
                  <span className="text-xs font-semibold text-[var(--muted)]">est. annual refund</span>
                </>
              )
            }
            if (period === 'seasonal') {
              const annual = monthly != null ? monthly * 12 : null
              return (
                <>
                  <span className="text-lg font-bold text-[var(--green-dark)]">{formatCurrency(annual)}</span>
                  <span className="text-xs font-semibold text-[var(--muted)]">seasonal payment est.</span>
                </>
              )
            }
            // monthly (default)
            return (
              <>
                <span className="text-lg font-bold text-[var(--green-dark)]">{formatCurrency(monthly)}</span>
                <span className="text-xs font-semibold text-[var(--muted)]">per month est.</span>
                {monthly > 0 && (
                  <span className="text-xs text-[var(--muted)]">{formatCurrency(monthly * 12)}/yr</span>
                )}
              </>
            )
          })()}
          <ChevronDown
            size={18}
            aria-hidden="true"
            className={`transition ${expanded ? 'rotate-180' : ''}`}
          />
        </div>
      </button>

      {expanded && (
        <div className="border-t border-[var(--line)] p-4">
          <div className="grid gap-5 md:grid-cols-2">
            <div>
              <h4 className="text-sm font-bold text-[var(--ink)]">Next steps</h4>
              <ol className="mt-2 space-y-2 text-sm leading-6 text-[var(--muted)]">
                {(benefit.next_steps || []).map((step) => (
                  <li key={step} className="flex gap-2">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--green)]" />
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </div>

            <div>
              <h4 className="text-sm font-bold text-[var(--ink)]">Documents to gather</h4>
              <ul className="mt-2 space-y-2 text-sm leading-6 text-[var(--muted)]">
                {(benefit.required_documents || []).slice(0, 7).map((document) => (
                  <li key={document} className="flex gap-2">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--coral)]" />
                    <span>{document}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => onSelect(benefit)}>
              View application guide
            </Button>
            {benefit.apply_url && (
              <a
                href={benefit.apply_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex min-h-10 items-center justify-center gap-2 rounded-md border border-[var(--line)] bg-white px-4 text-sm font-semibold text-[var(--ink)] hover:bg-[var(--mint)]"
              >
                <ExternalLink size={16} aria-hidden="true" />
                <span>Open application site</span>
              </a>
            )}
          </div>
        </div>
      )}
    </article>
  )
}

import { ArrowLeft, ExternalLink } from 'lucide-react'
import { formatCurrency } from '../../utils/formatting.js'
import Button from '../Shared/Button.jsx'

export default function ProgramDetail({ benefit, onBack }) {
  if (!benefit) return null

  return (
    <section className="mx-auto w-full max-w-4xl p-4 sm:p-6">
      <Button variant="quiet" onClick={onBack} className="mb-4 px-2">
        <ArrowLeft size={18} aria-hidden="true" />
        Back to results
      </Button>

      <div className="rounded-md border border-[var(--line)] bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-2xl font-bold">{benefit.program_name}</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">{benefit.reason}</p>
          </div>
          <div className="rounded-md bg-[var(--mint)] px-4 py-3 text-right">
            <p className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--green-dark)]">Estimate</p>
            <p className="text-2xl font-bold text-[var(--green-dark)]">
              {formatCurrency(benefit.estimated_monthly_value_usd)}
            </p>
          </div>
        </div>

        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <div>
            <h3 className="text-base font-bold">Application walkthrough</h3>
            <ol className="mt-3 space-y-3">
              {(benefit.next_steps || []).map((step, index) => (
                <li key={step} className="flex gap-3 text-sm leading-6 text-[var(--muted)]">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--green)] text-xs font-bold text-white">
                    {index + 1}
                  </span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </div>

          <div>
            <h3 className="text-base font-bold">Pre-application checklist</h3>
            <ul className="mt-3 space-y-2">
              {(benefit.required_documents || []).map((document) => (
                <li key={document} className="rounded-md border border-[var(--line)] px-3 py-2 text-sm text-[var(--muted)]">
                  {document}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-6 rounded-md bg-[#f7f8f4] p-4 text-sm leading-6 text-[var(--muted)]">
          Bring this checklist with you when you apply. The agency may ask for additional information, and calling 211 can help you find local application support.
        </div>

        {benefit.apply_url && (
          <a
            href={benefit.apply_url}
            target="_blank"
            rel="noreferrer"
            className="mt-5 inline-flex min-h-10 items-center justify-center gap-2 rounded-md bg-[var(--green)] px-4 text-sm font-semibold text-white hover:bg-[var(--green-dark)]"
          >
            <ExternalLink size={16} aria-hidden="true" />
            <span>Open application site</span>
          </a>
        )}
      </div>
    </section>
  )
}

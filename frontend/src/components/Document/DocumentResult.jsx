import { AlertCircle, CalendarDays, CheckCircle2, FileText } from 'lucide-react'

export default function DocumentResult({ result }) {
  if (!result) return null

  return (
    <article className="rounded-md border border-[var(--line)] bg-white p-5 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-[var(--mint)] text-[var(--green-dark)]">
          <FileText size={22} aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm font-bold uppercase tracking-[0.12em] text-[var(--green)]">Document type</p>
          <h2 className="text-2xl font-bold">{result.document_type}</h2>
        </div>
      </div>

      <p className="mt-5 text-base leading-7 text-[var(--ink)]">{result.plain_language_summary}</p>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <div className="rounded-md bg-[#f7f8f4] p-4">
          <div className="flex items-center gap-2 text-sm font-bold text-[var(--ink)]">
            <AlertCircle size={17} aria-hidden="true" />
            Action needed
          </div>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
            {result.action_required || 'No specific action was identified.'}
          </p>
        </div>

        <div className="rounded-md bg-[#f7f8f4] p-4">
          <div className="flex items-center gap-2 text-sm font-bold text-[var(--ink)]">
            <CalendarDays size={17} aria-hidden="true" />
            Deadline
          </div>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{result.deadline || 'No deadline found.'}</p>
        </div>
      </div>

      <div className="mt-5 flex items-center gap-2 rounded-md border border-[var(--line)] px-4 py-3 text-sm text-[var(--muted)]">
        <CheckCircle2 size={17} className="text-[var(--green)]" aria-hidden="true" />
        <span>{result.appeal_possible ? 'An appeal may be possible.' : 'No appeal option was clearly identified.'}</span>
      </div>

      <h3 className="mt-5 text-base font-bold">Next steps</h3>
      <ol className="mt-3 space-y-2">
        {(result.next_steps || []).map((step, index) => (
          <li key={step} className="flex gap-3 text-sm leading-6 text-[var(--muted)]">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--green)] text-xs font-bold text-white">
              {index + 1}
            </span>
            <span>{step}</span>
          </li>
        ))}
      </ol>
    </article>
  )
}

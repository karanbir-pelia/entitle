import { useState } from 'react'
import { formatCurrency } from '../../utils/formatting.js'
import { getTranslations } from '../../utils/i18n.js'
import BenefitsCard from './BenefitsCard.jsx'
import ProgramDetail from './ProgramDetail.jsx'

const CATEGORY_ORDER = ['food', 'healthcare', 'cash', 'utilities', 'housing', 'childcare']
const CATEGORY_LABELS = {
  food: 'Food Assistance',
  healthcare: 'Health Coverage',
  cash: 'Cash & Tax Credits',
  utilities: 'Utilities & Phone',
  housing: 'Housing',
  childcare: 'Child Care',
}

function groupByCategory(benefits) {
  const groups = {}
  for (const b of benefits) {
    const cat = b.category || 'other'
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(b)
  }
  // Return in preferred order, then any leftovers
  const ordered = []
  for (const cat of CATEGORY_ORDER) {
    if (groups[cat]) ordered.push({ category: cat, items: groups[cat] })
  }
  for (const [cat, items] of Object.entries(groups)) {
    if (!CATEGORY_ORDER.includes(cat)) ordered.push({ category: cat, items })
  }
  return ordered
}

export default function BenefitsList({ benefits, hasEstimatedValue, totalValue, annualCreditTotal, language }) {
  const [selected, setSelected] = useState(null)
  const txNoResults = getTranslations(language).noResults
  const tx = getTranslations(language).results

  if (selected) {
    return <ProgramDetail benefit={selected} onBack={() => setSelected(null)} />
  }

  const groups = groupByCategory(benefits)

  return (
    <section className="flex-1 overflow-y-auto bg-[#fbfaf7]">
      <div className="mx-auto max-w-4xl p-4 sm:p-6">
        <div className="mb-5 rounded-md border border-[var(--line)] bg-white p-5 shadow-sm">
          <p className="text-sm font-bold uppercase tracking-[0.12em] text-[var(--green)]">{tx.likelyMatches}</p>
          <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-2xl font-bold">{tx.benefitsHeader}</h2>
              <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
                {tx.estimatesNote}
              </p>
            </div>
            <div className="rounded-md bg-[var(--mint)] px-4 py-3 sm:text-right shrink-0">
              <p className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--green-dark)]">{tx.monthlyEstimate}</p>
              <p className="text-3xl font-bold text-[var(--green-dark)]">
                {benefits.length > 0 && !hasEstimatedValue ? tx.varies : formatCurrency(totalValue)}
              </p>
              {annualCreditTotal > 0 && (
                <p className="text-xs text-[var(--green-dark)] mt-0.5 opacity-75">
                  + {formatCurrency(annualCreditTotal)}{tx.perYear} {tx.annualCredits}
                </p>
              )}
            </div>
          </div>
        </div>

        {benefits.length === 0 ? (
          <div className="rounded-md border border-dashed border-[var(--line)] bg-white p-8 text-center">
            <h2 className="text-xl font-bold">{txNoResults.title}</h2>
            <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-[var(--muted)]">
              {txNoResults.desc}
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {groups.map(({ category, items }) => (
              <div key={category}>
                {groups.length > 1 && (
                  <h3 className="mb-2 text-xs font-bold uppercase tracking-[0.12em] text-[var(--muted)]">
                    {CATEGORY_LABELS[category] || category}
                  </h3>
                )}
                <div className="space-y-3">
                  {items.map((benefit) => (
                    <BenefitsCard key={benefit.program_id} benefit={benefit} onSelect={setSelected} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

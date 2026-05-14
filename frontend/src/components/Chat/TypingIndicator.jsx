import { useEffect, useState } from 'react'

const PHASES = [
  { at: 0, text: 'Reading your message…' },
  { at: 3500, text: 'Extracting your profile…' },
  { at: 7000, text: 'Checking eligibility…' },
  { at: 25000, text: 'Almost done…' },
]

export default function TypingIndicator() {
  const [phase, setPhase] = useState(0)

  useEffect(() => {
    setPhase(0)
    const timers = PHASES.slice(1).map(({ at }, i) =>
      setTimeout(() => setPhase(i + 1), at),
    )
    return () => timers.forEach(clearTimeout)
  }, [])

  return (
    <div className="flex max-w-[86%] items-center gap-2 rounded-md border border-[var(--line)] bg-white px-4 py-3 text-sm text-[var(--muted)]">
      <span className="flex gap-1" aria-hidden="true">
        <span className="h-2 w-2 animate-bounce rounded-full bg-[var(--green)] [animation-delay:-0.2s]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-[var(--green)] [animation-delay:-0.1s]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-[var(--green)]" />
      </span>
      <span className="transition-all duration-300">{PHASES[phase].text}</span>
    </div>
  )
}

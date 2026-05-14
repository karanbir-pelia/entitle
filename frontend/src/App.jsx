import { FileText, ListChecks, MessageCircle } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import BenefitsList from './components/Benefits/BenefitsList.jsx'
import ChatWindow from './components/Chat/ChatWindow.jsx'
import DocumentUpload from './components/Document/DocumentUpload.jsx'
import Header from './components/Layout/Header.jsx'
import { useChat } from './hooks/useChat.js'
import { useSession } from './hooks/useSession.js'
import { hasNumericEstimate } from './utils/formatting.js'
import { getTranslations, getWelcomeMessage } from './utils/i18n.js'

export default function App() {
  const { session, setSession, resetSession } = useSession()
  const [rightPanel, setRightPanel] = useState('results')
  const [mobileShowChat, setMobileShowChat] = useState(true)

  const tx = getTranslations(session.language)

  const chat = useChat({
    session,
    setSession,
    onBenefitsFound: () => {
      setRightPanel('results')
      setMobileShowChat(false)
    },
  })

  // When language changes and no user messages exist yet, replace the welcome message
  useEffect(() => {
    const hasUserMessages = session.messages.some((m) => m.role === 'user')
    if (!hasUserMessages) {
      setSession((s) => ({
        ...s,
        messages: [{ role: 'assistant', content: getWelcomeMessage(s.language) }],
      }))
    }
  }, [session.language]) // eslint-disable-line react-hooks/exhaustive-deps

  const benefits = session.benefits || []
  const hasEstimatedValue = useMemo(() => hasNumericEstimate(benefits), [benefits])
  // Monthly total: only programs paid on a recurring monthly basis
  const totalValue = useMemo(
    () =>
      benefits
        .filter((b) => !b.value_period || b.value_period === 'monthly')
        .reduce((sum, b) => sum + (b.estimated_monthly_value_usd || 0), 0),
    [benefits],
  )
  // Annual credits: EITC, CTC, seasonal payments — stored as monthly equivalents, displayed as yearly
  const annualCreditTotal = useMemo(
    () =>
      benefits
        .filter((b) => b.value_period === 'annual' || b.value_period === 'seasonal')
        .reduce((sum, b) => sum + (b.estimated_monthly_value_usd || 0) * 12, 0),
    [benefits],
  )

  const resultLabel =
    benefits.length > 0 ? `${tx.tabs.results} (${benefits.length})` : tx.tabs.results
  const mobileTab = mobileShowChat ? 'chat' : rightPanel

  function handleMobileTab(id) {
    if (id === 'chat') {
      setMobileShowChat(true)
    } else {
      setMobileShowChat(false)
      setRightPanel(id)
    }
  }

  const mobileTabs = [
    { id: 'chat', label: tx.tabs.chat, icon: MessageCircle },
    { id: 'results', label: resultLabel, icon: ListChecks },
    { id: 'document', label: tx.tabs.docs, icon: FileText },
  ]

  const desktopRightTabs = [
    { id: 'results', label: resultLabel, icon: ListChecks },
    { id: 'document', label: tx.tabs.docs, icon: FileText },
  ]

  return (
    <div className="app-root">
      <Header
        language={session.language}
        onLanguageChange={(language) => setSession((s) => ({ ...s, language }))}
        onReset={resetSession}
      />

      {/* Mobile top tab bar — sits below header, hidden on desktop */}
      <nav className="flex shrink-0 border-b border-[var(--line)] bg-white lg:hidden" aria-label="Main navigation">
        {mobileTabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => handleMobileTab(id)}
            className={`relative flex flex-1 flex-col items-center gap-0.5 py-2.5 text-xs font-semibold transition-colors ${
              mobileTab === id ? 'text-[var(--green)]' : 'text-[var(--muted)]'
            }`}
          >
            {mobileTab === id && (
              <span className="absolute bottom-0 left-2 right-2 h-0.5 rounded-t-full bg-[var(--green)]" aria-hidden="true" />
            )}
            <Icon size={18} aria-hidden="true" />
            <span>{label}</span>
          </button>
        ))}
      </nav>

      {/* Main content area */}
      <div className="content-area">
        {/* Left pane — Chat (always visible on desktop; full-screen on mobile when chat tab) */}
        <div
          className={`min-h-0 flex-col border-[var(--line)] lg:flex lg:flex-1 lg:border-r ${
            mobileShowChat ? 'flex flex-1' : 'hidden'
          }`}
        >
          <ChatWindow chat={chat} language={session.language} />
        </div>

        {/* Right pane — Results / Document (fixed 600px on desktop, full-screen on mobile when non-chat tab) */}
        <div
          className={`min-h-0 flex-col lg:flex lg:w-[600px] lg:flex-none ${
            mobileShowChat ? 'hidden' : 'flex flex-1'
          }`}
        >
          {/* Desktop-only tab strip */}
          <div className="hidden shrink-0 border-b border-[var(--line)] bg-white px-1 lg:flex">
            {desktopRightTabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => setRightPanel(id)}
                className={`flex h-11 items-center gap-1.5 border-b-2 px-4 text-sm font-semibold transition-colors ${
                  rightPanel === id
                    ? 'border-[var(--green)] text-[var(--green)]'
                    : 'border-transparent text-[var(--muted)] hover:text-[var(--ink)]'
                }`}
              >
                <Icon size={15} aria-hidden="true" />
                {label}
              </button>
            ))}
          </div>

          {/* Panel content */}
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            {rightPanel === 'results' ? (
              <BenefitsList
                benefits={benefits}
                hasEstimatedValue={hasEstimatedValue}
                totalValue={totalValue}
                annualCreditTotal={annualCreditTotal}
                language={session.language}
              />
            ) : (
              <DocumentUpload
                language={session.language}
                result={session.documentResult || null}
                onResultChange={(r) => setSession((s) => ({ ...s, documentResult: r }))}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

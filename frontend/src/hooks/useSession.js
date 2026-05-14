import { useEffect, useMemo, useState } from 'react'
import { getWelcomeMessage } from '../utils/i18n.js'

const STORAGE_KEY = 'entitle.session.v1'

function createInitialSession(language = 'en') {
  return {
    id: crypto.randomUUID(),
    language,
    benefits: [],
    profile: null,
    documentResult: null,
    messages: [{ role: 'assistant', content: getWelcomeMessage(language) }],
  }
}

export function useSession() {
  const initial = useMemo(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY)
      return stored ? JSON.parse(stored) : createInitialSession()
    } catch {
      return createInitialSession()
    }
  }, [])

  const [session, setSession] = useState(initial)

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
  }, [session])

  function resetSession() {
    setSession(createInitialSession())
  }

  return { session, setSession, resetSession }
}

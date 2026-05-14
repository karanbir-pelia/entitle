import { useState } from 'react'
import { sendChat } from '../services/api.js'

export function useChat({ session, setSession, onBenefitsFound }) {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  async function submitMessage(content) {
    const message = content.trim()
    if (!message || isLoading) return

    const history = session.messages
    const userMessage = { role: 'user', content: message }

    setError('')
    setIsLoading(true)
    setSession((current) => ({
      ...current,
      messages: [...current.messages, userMessage],
    }))

    try {
      const response = await sendChat({
        message,
        history,
        language: session.language,
        sessionId: session.id,
        profile: session.profile,
      })

      const assistantMessage = {
        role: 'assistant',
        content: response.reply,
      }

      setSession((current) => ({
        ...current,
        messages: [...current.messages, assistantMessage],
        benefits: response.benefits_found || current.benefits,
        profile: response.profile || current.profile,
      }))

      if (response.benefits_found?.length) {
        onBenefitsFound?.(response.benefits_found)
      }
    } catch (err) {
      setError(err.message || 'Could not reach Entitle')
      setSession((current) => ({
        ...current,
        messages: [
          ...current.messages,
          {
            role: 'assistant',
            content:
              'I could not reach the local model server. You can still use the direct eligibility check in the backend, or start Ollama and try again.',
          },
        ],
      }))
    } finally {
      setIsLoading(false)
    }
  }

  return {
    messages: session.messages,
    isLoading,
    error,
    submitMessage,
  }
}

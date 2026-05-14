const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

async function parseResponse(response) {
  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json') ? await response.json() : await response.text()

  if (!response.ok) {
    const message = typeof payload === 'string' ? payload : payload.detail || 'Request failed'
    throw new Error(message)
  }

  return payload
}

export async function sendChat({ message, history, language, sessionId, profile }) {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      history,
      language,
      session_id: sessionId,
      profile: profile || null,
    }),
  })

  return parseResponse(response)
}

export async function checkEligibility(profile) {
  const response = await fetch(`${API_BASE}/api/eligibility`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile }),
  })

  return parseResponse(response)
}

export async function readDocument({ file, language }) {
  const form = new FormData()
  form.append('file', file)
  form.append('language', language)

  const response = await fetch(`${API_BASE}/api/document`, {
    method: 'POST',
    body: form,
  })

  return parseResponse(response)
}

export async function getHealth() {
  const response = await fetch(`${API_BASE}/health`)
  return parseResponse(response)
}

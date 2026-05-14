import { SendHorizontal } from 'lucide-react'
import { useState } from 'react'
import { getTranslations } from '../../utils/i18n.js'
import Button from '../Shared/Button.jsx'

export default function InputBar({ disabled, onSubmit, language }) {
  const [value, setValue] = useState('')
  const placeholder = getTranslations(language).inputPlaceholder

  function submit(event) {
    event.preventDefault()
    const message = value.trim()
    if (!message) return
    onSubmit(message)
    setValue('')
  }

  return (
    <form onSubmit={submit} className="border-t border-[var(--line)] bg-white p-3">
      <div className="flex items-end gap-2">
        <label className="sr-only" htmlFor="message">
          Message
        </label>
        <textarea
          id="message"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              submit(event)
            }
          }}
          placeholder={placeholder}
          rows={1}
          disabled={disabled}
          className="max-h-36 min-h-12 flex-1 resize-none rounded-md border border-[var(--line)] bg-[#fbfaf7] px-4 py-3 text-sm leading-6 text-[var(--ink)] placeholder:text-[var(--muted)]"
        />
        <Button type="submit" disabled={disabled || !value.trim()} aria-label="Send message" className="h-12 px-4">
          <SendHorizontal size={18} aria-hidden="true" />
        </Button>
      </div>
    </form>
  )
}

import { useEffect, useRef } from 'react'
import InputBar from './InputBar.jsx'
import MessageBubble from './MessageBubble.jsx'
import TypingIndicator from './TypingIndicator.jsx'

export default function ChatWindow({ chat, language }) {
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [chat.messages, chat.isLoading])

  return (
    <section className="flex min-h-0 flex-1 flex-col">
      <div className="flex-1 overflow-y-auto bg-[#fbfaf7] p-4 sm:p-6">
        <div className="mx-auto flex max-w-3xl flex-col gap-4">
          {chat.messages.map((message, index) => (
            <MessageBubble key={`${message.role}-${index}`} message={message} />
          ))}
          {chat.isLoading && <TypingIndicator />}
          {chat.error && (
            <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              {chat.error}
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      <InputBar disabled={chat.isLoading} onSubmit={chat.submitMessage} language={language} />
    </section>
  )
}

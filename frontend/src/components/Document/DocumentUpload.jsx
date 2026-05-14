import { Camera, FileUp } from 'lucide-react'
import { useState } from 'react'
import { readDocument } from '../../services/api.js'
import { getTranslations } from '../../utils/i18n.js'
import Button from '../Shared/Button.jsx'
import Spinner from '../Shared/Spinner.jsx'
import DocumentResult from './DocumentResult.jsx'

const maxFileBytes = 8 * 1024 * 1024
const supportedTypes = new Set(['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif', 'application/pdf'])

export default function DocumentUpload({ language, result, onResultChange }) {
  const [file, setFile] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const tx = getTranslations(language).doc

  async function submit(event) {
    event.preventDefault()
    if (!file || isLoading) return

    setIsLoading(true)
    setError('')
    onResultChange(null)

    try {
      const response = await readDocument({ file, language })
      onResultChange(response)
    } catch (err) {
      setError(err.message || 'Could not read this document')
    } finally {
      setIsLoading(false)
    }
  }

  function chooseFile(nextFile) {
    onResultChange(null)

    if (!nextFile) {
      setFile(null)
      setError('')
      return
    }

    if (!supportedTypes.has(nextFile.type)) {
      setFile(null)
      setError('Upload a JPG, PNG, WebP, HEIC, HEIF photo, or a PDF.')
      return
    }

    if (nextFile.size > maxFileBytes) {
      setFile(null)
      setError('Upload a photo under 8 MB.')
      return
    }

    setError('')
    setFile(nextFile)
  }

  return (
    <section className="flex-1 overflow-y-auto bg-[#fbfaf7]">
      <div className="mx-auto max-w-4xl p-4 sm:p-6">
        <div className="rounded-md border border-[var(--line)] bg-white p-5 shadow-sm">
          <div className="flex items-start gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-[var(--mint)] text-[var(--green-dark)]">
              <Camera size={22} aria-hidden="true" />
            </div>
            <div>
              <h2 className="text-2xl font-bold">{tx.title}</h2>
              <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{tx.desc}</p>
            </div>
          </div>

          <form onSubmit={submit} className="mt-5">
            <label className="flex cursor-pointer flex-col items-center justify-center rounded-md border-2 border-dashed border-[var(--line)] bg-[#fbfaf7] px-4 py-8 text-center hover:border-[var(--green)]">
              <FileUp size={28} className="text-[var(--green)]" aria-hidden="true" />
              <span className="mt-3 text-sm font-bold text-[var(--ink)]">
                {file ? file.name : tx.choose}
              </span>
              <span className="mt-1 text-sm text-[var(--muted)]">{tx.fileHint}</span>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,image/heic,image/heif,application/pdf"
                className="sr-only"
                onChange={(event) => chooseFile(event.target.files?.[0] || null)}
              />
            </label>

            <div className="mt-4 flex items-center gap-3">
              <Button type="submit" disabled={!file || isLoading}>
                {isLoading ? tx.reading : tx.explain}
              </Button>
              {isLoading && <Spinner label="Using vision model" />}
            </div>
          </form>

          {error && (
            <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              {error}
            </div>
          )}
        </div>

        <div className="mt-5">
          <DocumentResult result={result} />
        </div>
      </div>
    </section>
  )
}

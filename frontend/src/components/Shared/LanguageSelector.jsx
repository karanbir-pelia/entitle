const languages = [
  { value: 'en', label: 'English', selectorLabel: 'Language' },
  { value: 'es', label: 'Español', selectorLabel: 'Idioma' },
  { value: 'zh', label: '中文', selectorLabel: '语言' },
  { value: 'vi', label: 'Tiếng Việt', selectorLabel: 'Ngôn ngữ' },
  { value: 'ar', label: 'العربية', selectorLabel: 'اللغة' },
  { value: 'fr', label: 'Français', selectorLabel: 'Langue' },
  { value: 'pt', label: 'Português', selectorLabel: 'Idioma' },
  { value: 'ko', label: '한국어', selectorLabel: '언어' },
]

export default function LanguageSelector({ value, onChange }) {
  const selected = languages.find((l) => l.value === value) || languages[0]
  return (
    <label className="inline-flex items-center gap-2 text-sm font-semibold text-[var(--muted)]">
      <span className="hidden sm:inline">{selected.selectorLabel}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 rounded-md border border-[var(--line)] bg-white px-3 text-sm text-[var(--ink)]"
      >
        {languages.map((language) => (
          <option key={language.value} value={language.value}>
            {language.label}
          </option>
        ))}
      </select>
    </label>
  )
}

export default function Button({
  children,
  type = 'button',
  variant = 'primary',
  className = '',
  ...props
}) {
  const variants = {
    primary: 'bg-[var(--green)] text-white hover:bg-[var(--green-dark)]',
    secondary: 'border border-[var(--line)] bg-white text-[var(--ink)] hover:bg-[var(--mint)]',
    quiet: 'text-[var(--muted)] hover:bg-[var(--mint)] hover:text-[var(--green-dark)]',
  }

  return (
    <button
      type={type}
      className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-4 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60 ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}

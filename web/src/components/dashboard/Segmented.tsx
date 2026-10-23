/** A small switch between two or three views of one card (pressed buttons in a labelled group, not tabs). */
export function Segmented<V extends string>({ label, options, value, onChange }: {
  label: string
  options: readonly { id: V; label: string }[]
  value: V
  onChange: (v: V) => void
}) {
  return (
    <div className="seg" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={o.id} type="button" aria-pressed={value === o.id} onClick={() => onChange(o.id)}>
          {o.label}
        </button>
      ))}
    </div>
  )
}

// Componentes visuales reutilizables (semáforo, tarjetas, estados).

const NIVEL_STYLE = {
  VERDE:    { bg: 'bg-verde/10',    text: 'text-verde',    dot: 'bg-verde',    label: 'Segura' },
  AMARILLO: { bg: 'bg-amarillo/10', text: 'text-amarillo', dot: 'bg-amarillo', label: 'En riesgo' },
  ROJO:     { bg: 'bg-rojo/10',     text: 'text-rojo',     dot: 'bg-rojo',     label: 'No segura' },
}

export function NivelBadge({ nivel }) {
  const s = NIVEL_STYLE[nivel] || { bg: 'bg-slate-100', text: 'text-slate-500', dot: 'bg-slate-400', label: 'Sin dato' }
  return (
    <span className={`badge ${s.bg} ${s.text}`}>
      <span className={`h-2 w-2 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  )
}

export function Semaforo({ nivel, size = 'md' }) {
  const on = { VERDE: 0, AMARILLO: 1, ROJO: 2 }[nivel]
  const dim = size === 'lg' ? 'h-5 w-5' : 'h-3.5 w-3.5'
  const luces = ['ROJO', 'AMARILLO', 'VERDE']
  const color = { ROJO: 'bg-rojo', AMARILLO: 'bg-amarillo', VERDE: 'bg-verde' }
  const idx = { ROJO: 2, AMARILLO: 1, VERDE: 0 }
  return (
    <div className="inline-flex flex-col items-center gap-1 rounded-md bg-slate-800 p-1.5">
      {luces.map((l) => (
        <span key={l}
          className={`${dim} rounded-full ${on === idx[l] ? color[l] : 'bg-slate-600/50'}`} />
      ))}
    </div>
  )
}

export function StatCard({ label, value, sub, accent = 'agua' }) {
  const ring = {
    agua: 'text-agua-700', verde: 'text-verde', amarillo: 'text-amarillo', rojo: 'text-rojo',
  }[accent]
  return (
    <div className="card">
      <p className="text-sm text-slate-500">{label}</p>
      <p className={`mt-1 text-3xl font-bold ${ring}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-400">{sub}</p>}
    </div>
  )
}

export function Spinner({ texto = 'Cargando…' }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-slate-500">
      <span className="h-6 w-6 animate-spin rounded-full border-2 border-agua-500 border-t-transparent" />
      {texto}
    </div>
  )
}

export function ViaRecepcion({ via }) {
  if (!via) return null
  const sms = via === 'ENVIADO_SMS'
  return (
    <span className={`badge ${sms ? 'bg-amber-100 text-amber-700' : 'bg-agua-100 text-agua-700'}`}>
      {sms ? '📶 SMS' : '🔄 Sincronizado'}
    </span>
  )
}

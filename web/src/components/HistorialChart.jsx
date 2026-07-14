import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ReferenceLine,
} from 'recharts'

export default function HistorialChart({ datos }) {
  const serie = datos.map((d) => ({
    fecha: new Date(d.fecha_hora).toLocaleDateString('es-PE', { day: '2-digit', month: '2-digit' }),
    cloro: d.cloro_mg_l,
    turbidez: d.turbidez_unt,
  }))

  if (!serie.length) {
    return <p className="text-sm text-slate-400 py-8 text-center">Sin historial para este reservorio.</p>
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={serie} margin={{ top: 8, right: 12, bottom: 0, left: -8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis dataKey="fecha" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 12 }} />
        <Tooltip />
        <Legend />
        {/* Umbrales normativos */}
        <ReferenceLine y={0.5} stroke="#15803d" strokeDasharray="4 4" label={{ value: 'Cl mín 0.5', fontSize: 10, fill: '#15803d' }} />
        <ReferenceLine y={5} stroke="#b91c1c" strokeDasharray="4 4" label={{ value: 'Turb máx 5', fontSize: 10, fill: '#b91c1c' }} />
        <Line type="monotone" dataKey="cloro" name="Cloro (mg/L)" stroke="#0891b2" strokeWidth={2} dot={{ r: 3 }} />
        <Line type="monotone" dataKey="turbidez" name="Turbidez (UNT)" stroke="#b45309" strokeWidth={2} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  )
}

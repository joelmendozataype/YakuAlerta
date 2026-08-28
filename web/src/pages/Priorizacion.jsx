import { useEffect, useState } from 'react'
import { api } from '../api'
import { NivelBadge, Spinner, StatCard } from '../components/ui'

/**
 * Vista de la Dirección Regional de Vivienda, Construcción y Saneamiento.
 *
 * Su pregunta no es «¿el agua es segura hoy?» sino **«¿dónde invertir?»**. Por
 * eso compara toda su jurisdicción de una vez, ordenada por criticidad: el
 * nivel de riesgo, la población afectada y el silencio de datos —que suele
 * delatar un sistema abandonado o sin operador.
 *
 * Antes obligaba a elegir un distrito y verlo por separado, que es pedirle que
 * compare de memoria justo lo que tiene que decidir. La criticidad la calcula
 * el servidor, para que el orden sea el mismo dondequiera que se consulte.
 */
export default function Priorizacion() {
  const [resumen, setResumen] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.priorizacion().then(setResumen).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="card text-rojo">{error}</div>
  if (!resumen) return <Spinner texto="Comparando su jurisdicción…" />

  const ranking = resumen.comunidades   // ya llega ordenada por criticidad

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Priorización territorial</h1>
        <p className="text-slate-500 text-sm">
          Dónde concentrar la inversión en saneamiento, según riesgo, población y silencio
          de datos · {resumen.distritos} distrito(s) con sistemas registrados.
        </p>
      </div>

      <div className="grid sm:grid-cols-4 gap-4">
        <StatCard label="Sistemas monitoreados" value={resumen.sistemas_monitoreados} />
        <StatCard label="Con agua segura" value={`${resumen.porcentaje_agua_segura}%`} accent="verde" />
        <StatCard label="Personas expuestas" value={resumen.poblacion_expuesta} accent="rojo" />
        <StatCard label="Sin reportar" value={resumen.reservorios_en_silencio} accent="amarillo"
          sub="Posible sistema abandonado" />
      </div>

      <div className="card">
        <h2 className="font-semibold text-slate-700">Comunidades por orden de atención</h2>
        <p className="text-xs text-slate-400 mt-0.5 mb-3">
          El silencio de datos suma criticidad: un reservorio que dejó de reportar suele ser
          uno sin operador o con la infraestructura fuera de servicio.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-slate-500 border-b">
              <tr>
                <th className="py-2">#</th>
                <th>Comunidad</th>
                <th>Distrito</th>
                <th>Estado</th>
                <th className="text-right">Población</th>
                <th className="text-right">Sin medir</th>
              </tr>
            </thead>
            <tbody>
              {ranking.map((c, i) => (
                <tr key={c.comunidad_id} className="border-b last:border-0">
                  <td className="py-2.5 text-slate-400 font-mono">{i + 1}</td>
                  <td>
                    <p className="font-medium text-slate-700">{c.comunidad}</p>
                    <p className="text-xs text-slate-400">{c.reservorio_codigo}</p>
                  </td>
                  <td className="text-slate-600">{c.distrito}</td>
                  <td><NivelBadge nivel={c.nivel} /></td>
                  <td className="text-right text-slate-600">{c.poblacion_servida ?? '—'}</td>
                  <td className="text-right">
                    {c.silencio
                      ? <span className="text-amarillo font-semibold">
                          {c.dias_sin_medir > 9000 ? 'sin registro' : `${c.dias_sin_medir} d`}
                        </span>
                      : <span className="text-slate-300">al día</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

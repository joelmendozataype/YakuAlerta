import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { NivelBadge, Spinner, StatCard } from '../components/ui'

/**
 * Vista de la DESA — autoridad sanitaria regional.
 *
 * Su aporte es lo que la medición de campo no alcanza: el **laboratorio**
 * (microbiológico, parasitológico y metales pesados) y el **dictamen** que
 * permite cerrar sanitariamente un caso rojo. Por eso su inicio muestra los
 * casos que esperan su pronunciamiento, no el semáforo operativo.
 */
export default function InicioDesa() {
  const [alertas, setAlertas] = useState([])
  const [error, setError] = useState('')
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    api.alertas('ACTIVA')
      .then(setAlertas)
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false))
  }, [])

  if (cargando) return <Spinner texto="Cargando casos abiertos…" />
  if (error) return <div className="card text-rojo">{error}</div>

  const rojas = alertas.filter((a) => a.nivel === 'ROJO')

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Vigilancia sanitaria regional</h1>
        <p className="text-slate-500 text-sm">
          Casos abiertos que pueden requerir análisis de laboratorio o dictamen sanitario.
        </p>
      </div>

      <div className="grid sm:grid-cols-3 gap-4">
        <StatCard label="Casos en rojo" value={rojas.length} accent="rojo"
          sub="Pueden requerir dictamen" />
        <StatCard label="Alertas abiertas" value={alertas.length} accent="amarillo" />
        <StatCard label="Laboratorio" value="Registrar" accent="agua"
          sub="Coliformes, parásitos, metales" />
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-slate-700">Casos abiertos</h2>
          <Link to="/laboratorio" className="btn-primary text-sm">🧪 Registrar resultado</Link>
        </div>

        {alertas.length === 0 ? (
          <p className="text-sm text-verde">No hay casos abiertos en la región.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-slate-500 border-b">
                <tr>
                  <th className="py-2">Comunidad</th>
                  <th>Estado</th>
                  <th className="text-right">Cloro</th>
                  <th className="text-right">Turbidez</th>
                  <th className="text-right">Desde</th>
                </tr>
              </thead>
              <tbody>
                {alertas.map((a) => (
                  <tr key={a.alerta_id} className="border-b last:border-0">
                    <td className="py-2.5">
                      <p className="font-medium text-slate-700">{a.comunidad}</p>
                      <p className="text-xs text-slate-400">{a.reservorio_codigo}</p>
                    </td>
                    <td><NivelBadge nivel={a.nivel} /></td>
                    <td className="text-right text-slate-600">{a.cloro_mg_l ?? '—'} mg/L</td>
                    <td className="text-right text-slate-600">{a.turbidez_unt ?? '—'} UNT</td>
                    <td className="text-right text-xs text-slate-500">
                      {new Date(a.fecha_generacion).toLocaleDateString('es-PE')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p className="text-xs text-slate-400 text-center">
        Un resultado de laboratorio no conforme fuerza el nivel rojo del reservorio hasta el
        cierre sanitario del caso (RF-15).
      </p>
    </div>
  )
}

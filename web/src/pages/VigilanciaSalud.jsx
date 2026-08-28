import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'
import { NivelBadge, Spinner, StatCard } from '../components/ui'

/**
 * Vista del establecimiento de salud (IPRESS) — HU-10.
 *
 * Su trabajo no es supervisar sistemas sino **anticipar casos**: necesita saber
 * qué comunidades tienen agua no segura, a cuánta gente alcanza y con qué
 * protocolo sanitario actuar.
 */
export default function VigilanciaSalud() {
  const { user } = useAuth()
  const [resumen, setResumen] = useState(null)
  const [alertas, setAlertas] = useState([])
  const [abierta, setAbierta] = useState(null)
  // Salud no cierra casos, pero sí necesita saber cuáles se resolvieron: es lo
  // que le permite levantar la vigilancia reforzada de EDA en una comunidad.
  const [estado, setEstado] = useState('ACTIVA')
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      user?.ubigeo_id ? api.tablero(user.ubigeo_id) : null,
      api.alertas(estado),
    ])
      .then(([t, a]) => {
        setResumen(t)
        // Lo rojo primero: es lo que obliga a actuar hoy.
        setAlertas([...a.filter((x) => x.nivel === 'ROJO'), ...a.filter((x) => x.nivel !== 'ROJO')])
      })
      .catch((e) => setError(e.message))
  }, [user, estado])

  if (error) return <div className="card text-rojo">{error}</div>
  if (!resumen && alertas.length === 0 && !error) return <Spinner texto="Cargando su jurisdicción…" />

  const rojas = alertas.filter((a) => a.nivel === 'ROJO').length

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Vigilancia sanitaria</h1>
        <p className="text-slate-500 text-sm">
          Comunidades con agua no segura en su jurisdicción y protocolo a aplicar.
        </p>
      </div>

      <div className="grid sm:grid-cols-3 gap-4">
        <StatCard label="Comunidades con agua no segura" value={rojas}
          accent={rojas > 0 ? 'rojo' : 'verde'} />
        <StatCard label="Personas expuestas" value={resumen?.poblacion_expuesta ?? '—'}
          sub="Reciben agua clasificada no segura" accent="rojo" />
        <StatCard label="Alertas abiertas" value={alertas.length} accent="amarillo" />
      </div>

      {rojas > 0 && (
        <div className="card bg-rojo/5 border-rojo/30">
          <p className="font-semibold text-rojo">Anticipe la vigilancia de EDA</p>
          <p className="text-sm text-slate-600 mt-1">
            Refuerce la búsqueda activa de casos de enfermedad diarreica aguda en las
            comunidades listadas y verifique que la población recibió la indicación de
            hervir el agua.
          </p>
        </div>
      )}

      <div className="card">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <h2 className="font-semibold text-slate-700">Casos de su jurisdicción</h2>
          <div className="inline-flex rounded-lg bg-slate-100 p-1 text-sm">
            {[['ACTIVA', 'En curso'], ['CERRADA', 'Resueltos']].map(([valor, rotulo]) => (
              <button key={valor} onClick={() => { setEstado(valor); setAbierta(null) }}
                className={`px-3 py-1 rounded-md ${estado === valor
                  ? 'bg-white shadow text-agua-700 font-medium' : 'text-slate-500'}`}>
                {rotulo}
              </button>
            ))}
          </div>
        </div>
        {alertas.length === 0 ? (
          <p className="text-sm text-verde">
            {estado === 'ACTIVA'
              ? 'No hay casos en curso. Se le avisará apenas se detecte uno.'
              : 'Todavía no hay casos resueltos.'}
          </p>
        ) : (
          <div className="space-y-2">
            {alertas.map((a) => (
              <div key={a.alerta_id} className="border border-slate-200 rounded-lg">
                <button
                  className="w-full flex items-center justify-between gap-3 p-3 text-left hover:bg-slate-50"
                  onClick={() => setAbierta(abierta === a.alerta_id ? null : a.alerta_id)}
                >
                  <div>
                    <p className="font-medium text-slate-700">{a.comunidad}</p>
                    <p className="text-xs text-slate-400">{a.reservorio_codigo}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <NivelBadge nivel={a.nivel} />
                    <span className="text-slate-400">{abierta === a.alerta_id ? '▲' : '▼'}</span>
                  </div>
                </button>

                {abierta === a.alerta_id && (
                  <div className="px-4 pb-4 space-y-3">
                    <p className="text-xs text-slate-500">
                      Cloro {a.cloro_mg_l ?? '—'} mg/L · Turbidez {a.turbidez_unt ?? '—'} UNT ·
                      Generada el {new Date(a.fecha_generacion).toLocaleDateString('es-PE')}
                    </p>
                    {a.protocolo && (
                      <pre className="whitespace-pre-wrap text-sm bg-slate-50 rounded-lg p-3 text-slate-700 font-sans">
                        {a.protocolo}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

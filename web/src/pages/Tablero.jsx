import { useEffect, useState } from 'react'
import { api } from '../api'
import { NivelBadge, Semaforo, StatCard, Spinner, ViaRecepcion } from '../components/ui'
import MapaRiesgo from '../components/MapaRiesgo'
import HistorialChart from '../components/HistorialChart'

export default function Tablero() {
  const [distritos, setDistritos] = useState([])
  const [ubigeoId, setUbigeoId] = useState(null)
  const [resumen, setResumen] = useState(null)
  const [cargando, setCargando] = useState(true)
  const [sel, setSel] = useState(null)      // reservorio seleccionado
  const [historial, setHistorial] = useState([])

  useEffect(() => {
    api.distritos().then((d) => {
      setDistritos(d)
      // El backend los devuelve con los que tienen comunidades al frente, así
      // que el primero es donde hay algo que ver.
      if (d.length) setUbigeoId(d[0].ubigeo_id)
    }).catch(() => setCargando(false))
  }, [])

  useEffect(() => {
    if (!ubigeoId) return
    setCargando(true)
    api.tablero(ubigeoId)
      .then((r) => setResumen(r))
      .finally(() => setCargando(false))
  }, [ubigeoId])

  // Descarga el afiche comunitario con QR para imprimir y fijar en el punto de agua.
  async function descargarAviso(c) {
    try {
      const blob = await api.avisoComunitario(c.comunidad_id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `aviso_${c.comunidad.toLowerCase().replace(/\s+/g, '_')}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      alert(`No se pudo generar el aviso: ${e.message}`)
    }
  }

  function verHistorial(c) {
    if (!c.reservorio_id) return
    setSel(c)
    api.historial(c.reservorio_id).then(setHistorial)
  }

  if (cargando && !resumen) return <Spinner texto="Cargando el distrito…" />
  if (!resumen) return <p className="text-slate-500">No hay datos disponibles.</p>

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Semáforo distrital</h1>
          <p className="text-slate-500 text-sm">Última medición por comunidad · regla de peor caso</p>
        </div>
        {/* Quien administra un solo distrito no elige: el selector le ofrecía
            doce y abría en el primero del abecedario, vacío y ajeno. */}
        {distritos.length > 1 ? (
          <select className="input max-w-xs" value={ubigeoId || ''}
            onChange={(e) => setUbigeoId(Number(e.target.value))}>
            {distritos.map((d) => (
              <option key={d.ubigeo_id} value={d.ubigeo_id}>
                {d.distrito} — {d.provincia}
                {d.comunidades ? ` (${d.comunidades})` : ' — sin comunidades'}
              </option>
            ))}
          </select>
        ) : (
          <p className="text-sm font-semibold text-agua-800">
            {distritos[0]?.distrito} — {distritos[0]?.provincia}
          </p>
        )}
      </div>

      {/* Indicadores del distrito */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Sistemas monitoreados" value={resumen.sistemas_monitoreados} />
        <StatCard label="Con agua segura" value={`${resumen.porcentaje_agua_segura}%`}
          accent={resumen.porcentaje_agua_segura >= 70 ? 'verde' : 'amarillo'} />
        <StatCard label="Alertas activas" value={resumen.alertas_activas}
          accent={resumen.alertas_activas ? 'rojo' : 'verde'} />
        <StatCard label="Silencio de datos" value={resumen.reservorios_en_silencio}
          accent={resumen.reservorios_en_silencio ? 'amarillo' : 'verde'} sub="reservorios sin medición" />
      </div>

      {/* Mapa + tabla */}
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="card p-0 overflow-hidden">
          <MapaRiesgo comunidades={resumen.comunidades} />
        </div>

        <div className="card overflow-hidden">
          <h2 className="font-semibold text-slate-700 mb-3">Comunidades</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-slate-500 border-b">
                <tr>
                  <th className="py-2">Comunidad</th>
                  <th>Estado</th>
                  <th>Vía</th>
                  <th className="text-right">Última</th>
                  <th className="text-right">Aviso</th>
                </tr>
              </thead>
              <tbody>
                {resumen.comunidades.map((c) => (
                  <tr key={c.comunidad_id}
                    className="border-b last:border-0 hover:bg-slate-50 cursor-pointer"
                    onClick={() => verHistorial(c)}>
                    <td className="py-2.5">
                      <div className="flex items-center gap-2">
                        <Semaforo nivel={c.nivel} />
                        <div>
                          <p className="font-medium text-slate-700">{c.comunidad}</p>
                          <p className="text-xs text-slate-400">{c.reservorio_codigo}</p>
                        </div>
                      </div>
                    </td>
                    <td>
                      <NivelBadge nivel={c.nivel} />
                      {c.silencio && <p className="text-[11px] text-amber-600 mt-0.5">⏰ silencio</p>}
                    </td>
                    <td><ViaRecepcion via={c.via_recepcion} /></td>
                    <td className="text-right text-xs text-slate-500">
                      {c.ultima_medicion
                        ? new Date(c.ultima_medicion).toLocaleDateString('es-PE')
                        : '—'}
                    </td>
                    <td className="text-right">
                      <button
                        title="Descargar el aviso para imprimir y fijar en el punto de agua"
                        className="text-agua-700 hover:text-agua-900 px-2 py-1 rounded hover:bg-agua-50"
                        onClick={(e) => { e.stopPropagation(); descargarAviso(c) }}
                      >
                        🖨️
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Historial del reservorio seleccionado */}
      {sel && (
        <div className="card">
          <div className="flex items-center justify-between mb-2">
            <h2 className="font-semibold text-slate-700">
              Historial · {sel.comunidad} ({sel.reservorio_codigo})
            </h2>
            <button className="btn-ghost text-sm" onClick={() => setSel(null)}>Cerrar</button>
          </div>
          <HistorialChart datos={historial} />
        </div>
      )}
    </div>
  )
}

import { useEffect, useState } from 'react'
import { api } from '../api'
import { NivelBadge, Spinner } from '../components/ui'

// Carga y muestra las fotos de evidencia de una alerta (HU-08).
function Evidencia({ ids }) {
  const [urls, setUrls] = useState([])
  useEffect(() => {
    let vivos = []
    Promise.all(ids.map((id) => api.evidenciaObjectUrl(id).catch(() => null)))
      .then((res) => { vivos = res.filter(Boolean); setUrls(vivos) })
    return () => vivos.forEach((u) => URL.revokeObjectURL(u))
  }, [ids])

  if (urls.length === 0) return null
  return (
    <div>
      <p className="font-semibold text-slate-700 text-sm mb-1">📷 Evidencia</p>
      <div className="flex gap-2 flex-wrap">
        {urls.map((u, i) => (
          <a key={i} href={u} target="_blank" rel="noreferrer">
            <img src={u} alt={`Evidencia ${i + 1}`}
              className="h-24 w-24 object-cover rounded-lg border border-slate-200" />
          </a>
        ))}
      </div>
    </div>
  )
}

export default function Alertas() {
  const [estado, setEstado] = useState('ACTIVA')
  const [alertas, setAlertas] = useState([])
  const [cargando, setCargando] = useState(true)
  const [sel, setSel] = useState(null)

  function cargar() {
    setCargando(true)
    api.alertas(estado).then(setAlertas).finally(() => setCargando(false))
  }
  useEffect(cargar, [estado])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Bandeja de alertas</h1>
          <p className="text-slate-500 text-sm">Trazabilidad detección → acción → verificación</p>
        </div>
        <div className="flex gap-1 bg-slate-200 rounded-lg p-1">
          {['ACTIVA', 'CERRADA'].map((e) => (
            <button key={e} onClick={() => setEstado(e)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium ${
                estado === e ? 'bg-white shadow text-agua-700' : 'text-slate-500'}`}>
              {e === 'ACTIVA' ? 'Activas' : 'Cerradas'}
            </button>
          ))}
        </div>
      </div>

      {cargando ? <Spinner /> : alertas.length === 0 ? (
        <div className="card text-center text-slate-500 py-12">
          🎉 No hay alertas {estado === 'ACTIVA' ? 'activas' : 'cerradas'}.
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {alertas.map((a) => (
            <button key={a.alerta_id} onClick={() => setSel(a)}
              className="card text-left hover:ring-2 hover:ring-agua-400 transition">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold text-slate-800">{a.comunidad}</p>
                  <p className="text-xs text-slate-400">Reservorio {a.reservorio_codigo} · #{a.alerta_id}</p>
                </div>
                <NivelBadge nivel={a.nivel} />
              </div>
              <div className="mt-3 flex gap-4 text-sm">
                <span>💧 Cloro: <b>{a.cloro_mg_l ?? '—'}</b> mg/L</span>
                <span>🌫️ Turbidez: <b>{a.turbidez_unt ?? '—'}</b> UNT</span>
              </div>
              <p className="mt-2 text-xs text-slate-400">
                {new Date(a.fecha_generacion).toLocaleString('es-PE')}
              </p>
            </button>
          ))}
        </div>
      )}

      {sel && <DetalleAlerta alerta={sel} onClose={() => setSel(null)} onCerrada={() => { setSel(null); cargar() }} />}
    </div>
  )
}

function DetalleAlerta({ alerta, onClose, onCerrada }) {
  const [detalle, setDetalle] = useState(alerta)
  const [remediciones, setRemediciones] = useState([])
  const [medicionCierre, setMedicionCierre] = useState('')
  const [resultado, setResultado] = useState('')
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    api.alerta(alerta.alerta_id).then(setDetalle)
    // Remediciones verdes candidatas del mismo reservorio
    if (alerta.reservorio_codigo) {
      api.alertas('CERRADA').catch(() => {})
    }
  }, [alerta])

  async function cerrar() {
    setError('')
    if (resultado.trim().length < 10) {
      setError('Describa la acción ejecutada: al menos 10 caracteres.')
      return
    }
    setEnviando(true)
    try {
      await api.cerrarAlerta(alerta.alerta_id, {
        medicion_cierre_id: medicionCierre ? Number(medicionCierre) : null,
        resultado_cierre: resultado,
      })
      onCerrada()
    } catch (e) {
      setError(e.message)
    } finally {
      setEnviando(false)
    }
  }

  const cerrada = detalle.estado === 'CERRADA'

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50" onClick={onClose}>
      <div className="bg-white rounded-xl max-w-lg w-full max-h-[90vh] overflow-y-auto p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-lg font-bold text-slate-800">{detalle.comunidad}</h3>
            <p className="text-sm text-slate-400">Reservorio {detalle.reservorio_codigo} · alerta #{detalle.alerta_id}</p>
          </div>
          <NivelBadge nivel={detalle.nivel} />
        </div>

        {/* Medición de origen */}
        <div className="bg-slate-50 rounded-lg p-3 text-sm grid grid-cols-2 gap-2">
          <span>💧 Cloro: <b>{detalle.cloro_mg_l ?? '—'}</b> mg/L</span>
          <span>🌫️ Turbidez: <b>{detalle.turbidez_unt ?? '—'}</b> UNT</span>
          <span className="col-span-2 text-xs text-slate-500">
            Medición de origen #{detalle.medicion_id} · {new Date(detalle.fecha_generacion).toLocaleString('es-PE')}
          </span>
        </div>

        {/* Evidencia fotográfica (HU-08) */}
        {detalle.evidencia_ids?.length > 0 && <Evidencia ids={detalle.evidencia_ids} />}

        {/* Protocolo */}
        {detalle.protocolo && (
          <div className="border-l-4 border-agua-500 bg-agua-50 p-3 rounded">
            <p className="font-semibold text-agua-800 text-sm mb-1">Protocolo de acción</p>
            <pre className="text-xs text-slate-600 whitespace-pre-wrap font-sans">{detalle.protocolo}</pre>
          </div>
        )}

        {/* Notificaciones */}
        {detalle.notificaciones?.length > 0 && (
          <details className="text-sm">
            <summary className="cursor-pointer text-slate-500">
              📨 {detalle.notificaciones.length} notificaciones enviadas
            </summary>
            <ul className="mt-2 space-y-1">
              {detalle.notificaciones.map((n) => (
                <li key={n.notificacion_id} className="text-xs text-slate-500">
                  {n.canal} → usuario #{n.usuario_id} · {n.estado_entrega}
                </li>
              ))}
            </ul>
          </details>
        )}

        {/* Cierre */}
        {cerrada ? (
          <div className="bg-verde/10 text-verde rounded-lg p-3 text-sm">
            ✅ Alerta cerrada · {detalle.resultado_cierre}
            {detalle.fecha_cierre && <p className="text-xs mt-1">{new Date(detalle.fecha_cierre).toLocaleString('es-PE')}</p>}
          </div>
        ) : (
          <div className="border-t pt-4 space-y-3">
            <p className="font-semibold text-slate-700 text-sm">Registrar cierre con evidencia</p>
            {detalle.nivel === 'ROJO' && (
              <div className="text-xs text-amber-700 bg-amber-50 rounded p-3 space-y-1">
                <p className="font-semibold">
                  Cerrar esta alerta le dice a la comunidad que puede volver a beber el agua.
                </p>
                <p>Por eso exige evidencia registrada (CA-HU16-02). Vale cualquiera de las dos:</p>
                <ul className="list-disc pl-4">
                  <li>Una <strong>remedición en VERDE</strong> del mismo reservorio, posterior a la alerta.</li>
                  <li>
                    Un <strong>resultado de laboratorio CONFORME</strong> posterior a la alerta.
                    Si la DESA ya lo registró, deje vacío el campo de abajo: el sistema lo busca.
                  </li>
                </ul>
              </div>
            )}
            <div>
              <label className="text-sm text-slate-600">
                N.º de remedición en verde <span className="text-slate-400">(opcional)</span>
              </label>
              <input className="input mt-1" value={medicionCierre}
                onChange={(e) => setMedicionCierre(e.target.value.replace(/\D/g, ''))}
                placeholder="Déjelo vacío si el cierre se apoya en el laboratorio" />
            </div>
            <div>
              <label className="text-sm text-slate-600">Acción ejecutada</label>
              <textarea className="input mt-1" rows={2} value={resultado}
                onChange={(e) => setResultado(e.target.value)}
                placeholder="Recloración realizada, remedición conforme…" />
            </div>
            {error && <p className="text-sm text-rojo bg-rojo/10 rounded px-3 py-2">{error}</p>}
            <div className="flex gap-2 justify-end">
              <button className="btn-ghost" onClick={onClose}>Cancelar</button>
              <button className="btn-primary" onClick={cerrar} disabled={enviando}>
                {enviando ? 'Cerrando…' : 'Cerrar alerta'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

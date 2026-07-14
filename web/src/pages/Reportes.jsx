import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Reportes() {
  const [distritos, setDistritos] = useState([])
  const [ubigeoId, setUbigeoId] = useState('')
  const [periodo, setPeriodo] = useState(new Date().toISOString().slice(0, 7))
  const [descargando, setDescargando] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api.distritos().then((d) => { setDistritos(d); if (d.length) setUbigeoId(d[0].ubigeo_id) })
  }, [])

  async function descargar(formato) {
    setError('')
    setDescargando(formato)
    try {
      const blob = await api.descargarReporte(ubigeoId, periodo, formato)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `vigilancia_${ubigeoId}_${periodo}.${formato}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e.message)
    } finally {
      setDescargando('')
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Reportes de vigilancia</h1>
        <p className="text-slate-500 text-sm">Consolidado mensual para remisión a la DIRESA/DESA (HU-17).</p>
      </div>

      <div className="card space-y-4">
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="text-sm text-slate-600">Distrito</label>
            <select className="input mt-1" value={ubigeoId} onChange={(e) => setUbigeoId(e.target.value)}>
              {distritos.map((d) => <option key={d.ubigeo_id} value={d.ubigeo_id}>{d.distrito}</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm text-slate-600">Periodo</label>
            <input type="month" className="input mt-1" value={periodo} onChange={(e) => setPeriodo(e.target.value)} />
          </div>
        </div>

        {error && <p className="text-sm text-rojo bg-rojo/10 rounded px-3 py-2">{error}</p>}

        <div className="flex gap-3">
          <button className="btn-primary" onClick={() => descargar('pdf')} disabled={!!descargando}>
            {descargando === 'pdf' ? 'Generando…' : '📄 Descargar PDF'}
          </button>
          <button className="btn-ghost" onClick={() => descargar('xlsx')} disabled={!!descargando}>
            {descargando === 'xlsx' ? 'Generando…' : '📊 Descargar Excel'}
          </button>
        </div>
        <p className="text-xs text-slate-400">
          El reporte consolida mediciones, semáforo y alertas por comunidad del periodo seleccionado.
        </p>
      </div>
    </div>
  )
}

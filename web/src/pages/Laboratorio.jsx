import { useEffect, useState } from 'react'
import { api } from '../api'
import { useAuth } from '../auth'

export default function Laboratorio() {
  const { user } = useAuth()
  const puedeRegistrar = ['DESA', 'ADMIN'].includes(user?.rol)

  const [distritos, setDistritos] = useState([])
  const [ubigeoId, setUbigeoId] = useState(null)
  const [comunidades, setComunidades] = useState([])
  const [form, setForm] = useState({
    reservorio_id: '', parametro: 'coliformes_totales', valor: '', unidad: 'UFC/100mL',
    dictamen: 'NO_CONFORME', fecha_muestreo: new Date().toISOString().slice(0, 10), laboratorio: '',
  })
  const [msg, setMsg] = useState(null)
  const [historial, setHistorial] = useState([])

  useEffect(() => {
    api.distritos().then((d) => { setDistritos(d); if (d.length) setUbigeoId(d[0].ubigeo_id) })
  }, [])

  useEffect(() => {
    if (!ubigeoId) return
    api.tablero(ubigeoId).then((r) => setComunidades(r.comunidades))
  }, [ubigeoId])

  async function verHistorial(reservorioId) {
    if (!reservorioId) return setHistorial([])
    try { setHistorial(await api.labReservorio(reservorioId)) } catch { setHistorial([]) }
  }

  async function enviar(e) {
    e.preventDefault()
    setMsg(null)
    try {
      await api.registrarLab({
        ...form,
        reservorio_id: Number(form.reservorio_id),
        valor: form.valor ? Number(form.valor) : null,
      })
      setMsg({ tipo: 'ok', texto: form.dictamen === 'NO_CONFORME'
        ? '✅ Resultado registrado. El reservorio pasa a ROJO hasta el cierre sanitario.'
        : '✅ Resultado conforme registrado.' })
      verHistorial(form.reservorio_id)
    } catch (err) {
      setMsg({ tipo: 'error', texto: err.message })
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Resultados de laboratorio</h1>
        <p className="text-slate-500 text-sm">Microbiológicos, parasitológicos y metales pesados (DESA).</p>
      </div>

      {!puedeRegistrar && (
        <div className="card bg-amber-50 border-amber-200 text-amber-800 text-sm">
          Solo el rol DESA (o ADMIN) puede registrar resultados. Puedes consultar el historial.
        </div>
      )}

      <form onSubmit={enviar} className="card grid sm:grid-cols-2 gap-4">
        <div className="sm:col-span-2">
          <label className="text-sm text-slate-600">Distrito</label>
          <select className="input mt-1" value={ubigeoId || ''} onChange={(e) => setUbigeoId(Number(e.target.value))}>
            {distritos.map((d) => <option key={d.ubigeo_id} value={d.ubigeo_id}>{d.distrito}</option>)}
          </select>
        </div>
        <div className="sm:col-span-2">
          <label className="text-sm text-slate-600">Reservorio</label>
          <select className="input mt-1" value={form.reservorio_id} required
            onChange={(e) => { setForm({ ...form, reservorio_id: e.target.value }); verHistorial(e.target.value) }}>
            <option value="">Seleccione…</option>
            {comunidades.filter((c) => c.reservorio_id).map((c) => (
              <option key={c.reservorio_id} value={c.reservorio_id}>{c.comunidad} — {c.reservorio_codigo}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-sm text-slate-600">Parámetro</label>
          <input className="input mt-1" value={form.parametro}
            onChange={(e) => setForm({ ...form, parametro: e.target.value })} />
        </div>
        <div>
          <label className="text-sm text-slate-600">Valor / Unidad</label>
          <div className="flex gap-2 mt-1">
            <input className="input" value={form.valor} onChange={(e) => setForm({ ...form, valor: e.target.value })} placeholder="Valor" />
            <input className="input w-28" value={form.unidad} onChange={(e) => setForm({ ...form, unidad: e.target.value })} />
          </div>
        </div>
        <div>
          <label className="text-sm text-slate-600">Dictamen</label>
          <select className="input mt-1" value={form.dictamen} onChange={(e) => setForm({ ...form, dictamen: e.target.value })}>
            <option value="CONFORME">CONFORME</option>
            <option value="NO_CONFORME">NO CONFORME</option>
          </select>
        </div>
        <div>
          <label className="text-sm text-slate-600">Fecha de muestreo</label>
          <input type="date" className="input mt-1" value={form.fecha_muestreo}
            onChange={(e) => setForm({ ...form, fecha_muestreo: e.target.value })} />
        </div>
        <div className="sm:col-span-2">
          <label className="text-sm text-slate-600">Laboratorio</label>
          <input className="input mt-1" value={form.laboratorio}
            onChange={(e) => setForm({ ...form, laboratorio: e.target.value })} placeholder="Laboratorio DIRESA HVCA" />
        </div>

        {msg && (
          <div className={`sm:col-span-2 text-sm rounded-lg px-3 py-2 ${
            msg.tipo === 'ok' ? 'bg-verde/10 text-verde' : 'bg-rojo/10 text-rojo'}`}>
            {msg.texto}
          </div>
        )}
        <div className="sm:col-span-2">
          <button className="btn-primary" disabled={!puedeRegistrar}>Registrar resultado</button>
        </div>
      </form>

      {historial.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-slate-700 mb-3">Historial del reservorio</h2>
          <table className="w-full text-sm">
            <thead className="text-left text-slate-500 border-b">
              <tr><th className="py-2">Parámetro</th><th>Valor</th><th>Dictamen</th><th>Muestreo</th></tr>
            </thead>
            <tbody>
              {historial.map((h) => (
                <tr key={h.resultado_id} className="border-b last:border-0">
                  <td className="py-2">{h.parametro}</td>
                  <td>{h.valor ?? '—'} {h.unidad}</td>
                  <td>
                    <span className={`badge ${h.dictamen === 'NO_CONFORME' ? 'bg-rojo/10 text-rojo' : 'bg-verde/10 text-verde'}`}>
                      {h.dictamen}
                    </span>
                  </td>
                  <td>{h.fecha_muestreo}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

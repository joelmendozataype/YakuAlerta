import { useEffect, useState } from 'react'
import { useAuth } from '../auth'
import { api } from '../api'
import { Spinner } from '../components/ui'

/**
 * Rastro de auditoría.
 *
 * El sistema ya registraba cada hecho sensible, pero nadie podía leerlo. Un
 * rastro que no se consulta no sirve para rendir cuentas, que es para lo que
 * existe: si una comunidad cambió de color, aquí está por qué y por obra de
 * quién.
 */

// Acciones que cambian el comportamiento del sistema o el acceso de alguien.
const SENSIBLE = new Set([
  'CAMBIA_UMBRAL', 'CIERRE_ALERTA', 'BAJA_USUARIO', 'RESET_CLAVE', 'EDITA_USUARIO',
])

const ENTIDAD = {
  usuario: 'Cuenta',
  alerta: 'Alerta',
  parametro_normativo: 'Umbral',
}

function fecha(iso) {
  const d = new Date(iso)
  return d.toLocaleString('es-PE', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function Fila({ h }) {
  const marcado = SENSIBLE.has(h.accion)
  return (
    <tr className={marcado ? 'bg-amarillo/5' : ''}>
      <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-400">
        {fecha(h.fecha_hora)}
      </td>
      <td className="px-4 py-3">
        <p className="text-sm font-medium text-slate-800">{h.titulo}</p>
        {h.detalle && <p className="text-xs text-slate-500">{h.detalle}</p>}
      </td>
      <td className="px-4 py-3 text-sm">
        {h.usuario ? (
          <>
            <p className="text-slate-700">{h.usuario}</p>
            <p className="text-xs text-slate-400">{h.rol}</p>
          </>
        ) : (
          <span className="text-slate-300">—</span>
        )}
      </td>
      <td className="px-4 py-3 text-xs text-slate-400 whitespace-nowrap">
        {h.entidad_afectada
          ? `${ENTIDAD[h.entidad_afectada] || h.entidad_afectada} #${h.registro_id}`
          : '—'}
      </td>
    </tr>
  )
}

export default function Auditoria() {
  const { user } = useAuth()
  const [hechos, setHechos] = useState(null)
  const [acciones, setAcciones] = useState({})
  const [filtros, setFiltros] = useState({ accion: '', solo_sensibles: false })
  const [error, setError] = useState('')

  useEffect(() => {
    api.accionesAuditables().then(setAcciones).catch(() => setAcciones({}))
  }, [])

  useEffect(() => {
    setHechos(null)
    api.auditoria({ ...filtros, limite: 200 })
      .then(setHechos)
      .catch((e) => setError(e.message))
  }, [filtros])

  if (error) return <div className="card text-rojo">{error}</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-agua-800">Rastro de auditoría</h1>
        <p className="text-sm text-slate-500">
          Quién hizo qué y sobre qué ·{' '}
          {user?.rol === 'ADMIN' ? 'todo el ámbito regional' : 'su distrito'}
        </p>
      </div>

      <div className="card flex flex-wrap items-end gap-4">
        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Acción
          </span>
          <select className="input mt-1 min-w-64" value={filtros.accion}
            onChange={(e) => setFiltros({ ...filtros, accion: e.target.value })}>
            <option value="">Todas</option>
            {Object.entries(acciones).map(([clave, titulo]) => (
              <option key={clave} value={clave}>{titulo}</option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-2 pb-2 text-sm text-slate-600">
          <input type="checkbox" checked={filtros.solo_sensibles}
            onChange={(e) => setFiltros({ ...filtros, solo_sensibles: e.target.checked })} />
          Solo hechos que cambian el sistema
        </label>

        {(filtros.accion || filtros.solo_sensibles) && (
          <button className="btn-ghost pb-2"
            onClick={() => setFiltros({ accion: '', solo_sensibles: false })}>
            Quitar filtros
          </button>
        )}
      </div>

      {!hechos ? (
        <Spinner texto="Leyendo el rastro…" />
      ) : hechos.length === 0 ? (
        <div className="card text-slate-500">No hay hechos registrados con ese filtro.</div>
      ) : (
        <div className="card p-0 overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-semibold">Cuándo</th>
                <th className="px-4 py-3 font-semibold">Qué ocurrió</th>
                <th className="px-4 py-3 font-semibold">Quién</th>
                <th className="px-4 py-3 font-semibold">Sobre</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {hechos.map((h) => <Fila key={h.auditoria_id} h={h} />)}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-slate-400">
        El rastro no se puede editar ni borrar desde el sistema: es la prueba de que cada
        alerta cerrada y cada umbral movido tuvieron un responsable.
      </p>
    </div>
  )
}

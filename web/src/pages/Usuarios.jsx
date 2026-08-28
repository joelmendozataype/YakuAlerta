import { useEffect, useState } from 'react'
import { useAuth } from '../auth'
import { api } from '../api'
import { Spinner } from '../components/ui'
import Actores from '../components/Actores'

/**
 * Padrón de cuentas del sistema.
 *
 * La ATM administra las de su distrito; el ADMIN, las de toda la región. Los
 * candados viven en el backend —la ATM no sale de su distrito ni crea cuentas
 * de rango superior—; aquí solo se evita ofrecer lo que se sabe que será
 * rechazado, para no hacer perder el tiempo a quien administra.
 */

// Toda cuenta pertenece a uno de los siete actores. Dos de ellos agrupan más
// de una función, y solo ahí hace falta precisarla: en los demás, el nombre
// del actor ya dice todo.
const FUNCION = {
  OPERADOR: 'Operador · mide el reservorio',
  DIRECTIVO_JASS: 'Directivo · preside la junta',
  ATM: 'Área Técnica Municipal',
  AUTORIDAD_LOCAL: 'Autoridad local',
}

// Roles que la ATM puede dar de alta; el resto son de alcance regional y los
// crea solo el ADMIN. El backend lo vuelve a verificar.
const ROLES_DE_CAMPO = ['OPERADOR', 'DIRECTIVO_JASS', 'AUTORIDAD_LOCAL', 'POBLACION']

const vacio = {
  nombres: '', dni: '', telefono: '', clave: '',
  rol: 'OPERADOR', entidad: '', comunidad_id: '',
}

function Formulario({ esAdmin, actores, comunidades, onCreado, onCancelar }) {
  const [f, setF] = useState(vacio)
  const [error, setError] = useState('')
  const [guardando, setGuardando] = useState(false)

  // El desplegable se agrupa por actor: primero se elige a quién representa la
  // persona y recién después, si el actor tiene más de una, su función.
  const grupos = actores
    .map((a) => ({
      actor: a.actor,
      roles: a.roles.filter((r) => esAdmin || ROLES_DE_CAMPO.includes(r)),
    }))
    .filter((g) => g.roles.length > 0)

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  async function enviar(e) {
    e.preventDefault()
    if (f.dni.length !== 8) return setError('El DNI debe tener 8 dígitos.')
    if (f.clave.length < 8) return setError('La clave debe tener al menos 8 caracteres.')
    setError('')
    setGuardando(true)
    try {
      await api.crearUsuario({
        ...f,
        comunidad_id: f.comunidad_id ? Number(f.comunidad_id) : null,
        entidad: f.entidad || null,
      })
      setF(vacio)
      onCreado()
    } catch (err) {
      setError(err.message)
    } finally {
      setGuardando(false)
    }
  }

  return (
    <form onSubmit={enviar} className="card">
      <h2 className="font-semibold text-agua-800">Registrar una cuenta</h2>

      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Nombres y apellidos
          </span>
          <input className="input mt-1" value={f.nombres} onChange={set('nombres')} required />
        </label>

        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">DNI</span>
          <input className="input mt-1" value={f.dni} inputMode="numeric" maxLength={8}
            onChange={(e) => setF({ ...f, dni: e.target.value.replace(/\D/g, '') })}
            placeholder="70100001" required />
        </label>

        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Celular
          </span>
          <input className="input mt-1" value={f.telefono} inputMode="numeric" maxLength={9}
            onChange={(e) => setF({ ...f, telefono: e.target.value.replace(/\D/g, '') })}
            placeholder="987000001" required />
        </label>

        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Actor
          </span>
          <select className="input mt-1" value={f.rol} onChange={set('rol')}>
            {grupos.map((g) => (
              <optgroup key={g.actor} label={g.actor}>
                {g.roles.map((r) => (
                  <option key={r} value={r}>{FUNCION[r] || g.actor}</option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Comunidad
          </span>
          <select className="input mt-1" value={f.comunidad_id} onChange={set('comunidad_id')}>
            <option value="">Sin comunidad (ámbito distrital)</option>
            {comunidades.map((c) => (
              <option key={c.comunidad_id} value={c.comunidad_id}>{c.nombre}</option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Entidad
          </span>
          <input className="input mt-1" value={f.entidad} onChange={set('entidad')}
            placeholder="JASS Comunidad 01" />
        </label>

        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Clave inicial
          </span>
          <input className="input mt-1" type="password" value={f.clave} onChange={set('clave')}
            placeholder="mínimo 8 caracteres" required />
        </label>
      </div>

      {error && <p className="mt-4 text-sm text-rojo bg-rojo/10 rounded-lg px-3 py-2">{error}</p>}

      <div className="mt-5 flex gap-3">
        <button className="btn-primary" disabled={guardando}>
          {guardando ? 'Registrando…' : 'Registrar'}
        </button>
        <button type="button" className="btn-ghost" onClick={onCancelar}>Cancelar</button>
      </div>
    </form>
  )
}

function Fila({ u, yo, actorDe, onCambio, onClave }) {
  const [ocupado, setOcupado] = useState(false)
  const esYo = u.usuario_id === yo?.usuario_id

  async function alternar() {
    setOcupado(true)
    try { await onCambio(u, { activo: !u.activo }) } finally { setOcupado(false) }
  }

  return (
    <tr className={u.activo ? '' : 'bg-slate-50 text-slate-400'}>
      <td className="px-4 py-3">
        <p className="font-medium text-slate-800">{u.nombres}</p>
        <p className="text-xs text-slate-400">DNI {u.dni || '—'} · {u.telefono}</p>
      </td>
      <td className="px-4 py-3 text-sm">
        <p className="font-medium">{actorDe[u.rol] || u.rol}</p>
        <p className="text-xs text-slate-400">
          {[FUNCION[u.rol], u.entidad].filter(Boolean).join(' · ')}
        </p>
      </td>
      <td className="px-4 py-3 text-sm text-slate-500">{u.comunidad || u.distrito || '—'}</td>
      <td className="px-4 py-3">
        <span className={`badge ${u.activo ? 'bg-verde/10 text-verde' : 'bg-slate-200 text-slate-500'}`}>
          {u.activo ? 'Activa' : 'De baja'}
        </span>
      </td>
      <td className="px-4 py-3 text-right whitespace-nowrap">
        {esYo ? (
          <span className="text-xs text-slate-400">Su cuenta</span>
        ) : (
          <>
            <button className="text-sm text-agua-700 hover:underline disabled:opacity-40"
              onClick={() => onClave(u)} disabled={ocupado}>
              Clave
            </button>
            <button className={`ml-4 text-sm hover:underline disabled:opacity-40 ${
              u.activo ? 'text-rojo' : 'text-verde'}`}
              onClick={alternar} disabled={ocupado}>
              {u.activo ? 'Dar de baja' : 'Reactivar'}
            </button>
          </>
        )}
      </td>
    </tr>
  )
}

export default function Usuarios() {
  const { user } = useAuth()
  const esAdmin = user?.rol === 'ADMIN'

  const [usuarios, setUsuarios] = useState(null)
  // Los actores se cargan una sola vez y se comparten: la tabla de arriba y
  // cada fila del padrón deben nombrar al mismo actor con la misma palabra.
  const [actores, setActores] = useState(null)
  const [comunidades, setComunidades] = useState([])
  const [creando, setCreando] = useState(false)
  const [error, setError] = useState('')
  const [temporal, setTemporal] = useState(null)

  function cargar() {
    api.usuarios().then(setUsuarios).catch((e) => setError(e.message))
    api.actores().then(setActores).catch((e) => setError(e.message))
  }

  useEffect(() => {
    cargar()
    api.comunidades().then(setComunidades).catch(() => setComunidades([]))
  }, [])

  async function cambiar(u, payload) {
    setError('')
    try {
      await api.corregirUsuario(u.usuario_id, payload)
      cargar()
    } catch (e) {
      setError(e.message)
    }
  }

  async function clave(u) {
    setError('')
    try {
      setTemporal(await api.restablecerClave(u.usuario_id))
    } catch (e) {
      setError(e.message)
    }
  }

  if (!usuarios || !actores) return <Spinner texto="Cargando el padrón de cuentas…" />

  const activas = usuarios.filter((u) => u.activo).length
  // Rol interno → actor al que representa, según lo declara el backend.
  const actorDe = Object.fromEntries(
    actores.flatMap((a) => a.roles.map((r) => [r, a.actor])),
  )

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-agua-800">Cuentas del sistema</h1>
          <p className="text-sm text-slate-500">
            {activas} activas de {usuarios.length} ·{' '}
            {esAdmin ? 'todo el ámbito regional' : 'su distrito'}
          </p>
        </div>
        {!creando && (
          <button className="btn-primary" onClick={() => setCreando(true)}>
            + Registrar cuenta
          </button>
        )}
      </div>

      <Actores actores={actores} />

      {error && <div className="card text-rojo">{error}</div>}

      {temporal && (
        <div className="card border-amarillo bg-amarillo/5">
          <h2 className="font-semibold text-slate-800">Clave provisional generada</h2>
          <p className="mt-1 text-sm text-slate-600">
            Entréguesela a <strong>{temporal.nombres}</strong> en persona. No volverá a
            mostrarse: si la pierde, genere otra.
          </p>
          <p className="mt-3 font-mono text-2xl tracking-widest text-agua-800">
            {temporal.clave_temporal}
          </p>
          <button className="btn-ghost mt-4" onClick={() => setTemporal(null)}>
            Ya la anoté
          </button>
        </div>
      )}

      {creando && (
        <Formulario esAdmin={esAdmin} actores={actores} comunidades={comunidades}
          onCancelar={() => setCreando(false)}
          onCreado={() => { setCreando(false); cargar() }} />
      )}

      <div className="card overflow-x-auto p-0">
        <table className="w-full text-left">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3 font-semibold">Persona</th>
              <th className="px-4 py-3 font-semibold">Actor</th>
              <th className="px-4 py-3 font-semibold">Ámbito</th>
              <th className="px-4 py-3 font-semibold">Estado</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {usuarios.map((u) => (
              <Fila key={u.usuario_id} u={u} yo={user} actorDe={actorDe}
                onCambio={cambiar} onClave={clave} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

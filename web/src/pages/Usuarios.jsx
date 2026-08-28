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

// Actores que la ATM puede dar de alta; los demás son de alcance regional y
// los registra solo el ADMIN. El backend lo vuelve a verificar.
const ACTORES_DE_CAMPO = ['JASS', 'USUARIO']

const vacio = {
  nombres: '', dni: '', telefono: '', clave: '',
  rol: 'OPERADOR', ubigeo_id: '', comunidad_nombre: '',
}

// Qué territorio pide cada ámbito, dicho para quien registra la cuenta.
const AMBITO = {
  comunidad: 'Trabaja en una comunidad concreta: indique cuál.',
  distrito: 'Alcance distrital: cubre todo el distrito, no una sola comunidad.',
  regional: 'Alcance regional: no se asigna a un territorio.',
}

function Formulario({ esAdmin, actores, comunidades, ubigeos, onCreado, onCancelar }) {
  const [f, setF] = useState(vacio)
  const [error, setError] = useState('')
  const [guardando, setGuardando] = useState(false)

  // Se elige un actor, no un rol interno: son los mismos siete de la tabla de
  // arriba. Cada uno se registra con su rol principal.
  const disponibles = actores.filter(
    (a) => esAdmin || ACTORES_DE_CAMPO.includes(a.grupo),
  )


  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  // El actor decide qué territorio hace falta: la comunidad solo la escribe
  // quien trabaja en una; el distrito lo necesita también el ámbito distrital;
  // el regional no pide ninguno.
  const actor = actores.find((a) => a.rol_principal === f.rol)
  const esComunal = actor?.ambito === 'comunidad'
  // Solo la JASS estrena comunidad: es quien administra su sistema de agua.
  const esJass = actor?.grupo === 'JASS'
  const pideDistrito = actor?.ambito !== 'regional'

  // La ATM registra siempre en el suyo; el ADMIN elige.
  const unico = ubigeos.length === 1 ? ubigeos[0] : null
  const ubigeoId = unico ? unico.ubigeo_id : f.ubigeo_id
  const distrito = ubigeos.find((u) => String(u.ubigeo_id) === String(ubigeoId))

  // Las comunidades varían y no hay padrón: se escriben. Si ya existe una con
  // ese nombre en el distrito se reutiliza, y no se crea un reservorio nuevo.
  const nombreLimpio = f.comunidad_nombre.trim()
  const yaExiste = comunidades.find(
    (c) => c.nombre.toLowerCase() === nombreLimpio.toLowerCase()
      && String(c.ubigeo_id) === String(ubigeoId),
  )
  const entidad = esComunal
    ? (nombreLimpio ? (yaExiste?.jass_nombre || `JASS ${nombreLimpio}`) : null)
    : actor?.entidad_ejemplo

  async function enviar(e) {
    e.preventDefault()
    if (f.dni.length !== 8) return setError('El DNI debe tener 8 dígitos.')
    if (f.clave.length < 8) return setError('La clave debe tener al menos 8 caracteres.')
    if (pideDistrito && !ubigeoId) return setError('Elija el distrito.')
    if (esComunal && !nombreLimpio) return setError('Escriba el nombre de la comunidad.')
    setError('')
    setGuardando(true)
    try {
      const creada = await api.crearUsuario({
        ...f,
        ubigeo_id: pideDistrito ? Number(ubigeoId) : null,
        comunidad_nombre: esComunal ? nombreLimpio : null,
      })
      onCreado(creada)
      setF(vacio)
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
          <select className="input mt-1" value={f.rol}
            onChange={(e) => {
              const nuevo = actores.find((a) => a.rol_principal === e.target.value)
              setF({
                ...f, rol: e.target.value,
                comunidad_nombre: nuevo?.ambito === 'comunidad' ? f.comunidad_nombre : '',
              })
            }}>
            {disponibles.map((a) => (
              <option key={a.grupo} value={a.rol_principal}>{a.actor}</option>
            ))}
          </select>
          {actor && (
            <span className="mt-1 block text-xs text-slate-400">{AMBITO[actor.ambito]}</span>
          )}
        </label>

        {/* El territorio va de lo general a lo particular: provincia,
            distrito y —solo para quien trabaja en una— comunidad. */}
        {pideDistrito && (
          <>
            <div className="block">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Provincia
              </span>
              <p className="input mt-1 bg-slate-50 text-slate-600">
                {distrito?.provincia || ubigeos[0]?.provincia || '—'}
              </p>
            </div>

            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Distrito <span className="text-rojo">*</span>
              </span>
              {unico ? (
                <p className="input mt-1 bg-slate-50 text-slate-600">{unico.distrito}</p>
              ) : (
                <select className="input mt-1" value={f.ubigeo_id}
                  onChange={set('ubigeo_id')} required>
                  <option value="">Seleccione…</option>
                  {ubigeos.map((u) => (
                    <option key={u.ubigeo_id} value={u.ubigeo_id}>{u.distrito}</option>
                  ))}
                </select>
              )}
            </label>
          </>
        )}

        {/* Las comunidades varían de distrito en distrito y no hay padrón del
            que leerlas: se escriben. Si ya existe una con ese nombre se
            reutiliza en vez de duplicarla. */}
        {esComunal && (
          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Comunidad <span className="text-rojo">*</span>
            </span>
            <input className="input mt-1" value={f.comunidad_nombre}
              onChange={set('comunidad_nombre')} placeholder="COM-04" required
              list="comunidades-registradas" />
            <datalist id="comunidades-registradas">
              {comunidades
                .filter((c) => String(c.ubigeo_id) === String(ubigeoId))
                .map((c) => <option key={c.comunidad_id} value={c.nombre} />)}
            </datalist>
            <span className="mt-1 block text-xs text-slate-400">
              {yaExiste
                ? 'Ya registrada: la cuenta se suma a esa junta.'
                : esJass
                  ? 'Si no existe, se creará con su JASS y su primer reservorio.'
                  : 'Debe estar registrada: se crea al dar de alta su JASS.'}
            </span>
          </label>
        )}

        {/* El reservorio no se nombra: su código lo arma la estructura. */}
        {esJass && (
          <div className="block">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Reservorio
            </span>
            <p className="input mt-1 bg-slate-50 text-slate-600 truncate font-mono text-sm">
              {yaExiste
                ? '—'
                : (nombreLimpio && distrito
                  ? `R#-${distrito.distrito}-${nombreLimpio.toUpperCase()}`
                  : '—')}
            </p>
            <span className="mt-1 block text-xs text-slate-400">
              {yaExiste
                ? 'La comunidad ya tiene el suyo.'
                : 'Se genera con la estructura al registrar.'}
            </span>
          </div>
        )}

        {/* La entidad tampoco se teclea: se desprende del actor y su territorio. */}
        <div className="block">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Entidad
          </span>
          <p className="input mt-1 bg-slate-50 text-slate-600 truncate">
            {entidad || '—'}
          </p>
          <span className="mt-1 block text-xs text-slate-400">
            Se asigna sola, según el actor y su territorio.
          </span>
        </div>

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
        {u.entidad && <p className="text-xs text-slate-400">{u.entidad}</p>}
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
  const [ubigeos, setUbigeos] = useState([])
  const [creado, setCreado] = useState(null)
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
    api.ubigeos().then(setUbigeos).catch(() => setUbigeos([]))
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

      {creado && (
        <div className="card border-verde bg-verde/5">
          <h2 className="font-semibold text-slate-800">
            Se registró la comunidad {creado.comunidad_creada}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Junto con la cuenta nació su junta{' '}
            <strong>{creado.entidad}</strong> y su primer reservorio{' '}
            <span className="font-mono">{creado.reservorio_creado}</span>. Complete
            el volumen del reservorio desde la pantalla «JASS».
          </p>
          <button className="btn-ghost mt-4" onClick={() => setCreado(null)}>Entendido</button>
        </div>
      )}

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
          ubigeos={ubigeos}
          onCancelar={() => setCreando(false)}
          onCreado={(u) => {
            setCreando(false)
            setCreado(u.comunidad_creada ? u : null)
            cargar()
            api.comunidades().then(setComunidades).catch(() => {})
          }} />
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

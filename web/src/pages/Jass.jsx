import { useEffect, useState } from 'react'
import { useAuth } from '../auth'
import { api } from '../api'
import { NivelBadge, Spinner, StatCard } from '../components/ui'

/**
 * Directorio de JASS que acompaña la ATM.
 *
 * Una JASS por comunidad —administra un solo sistema de agua— y una ATM por
 * distrito, que acompaña a todas. Esta pantalla responde la pregunta diaria de
 * la ATM: ¿cuál de mis juntas necesita que la visite hoy?
 */

const ROL = { OPERADOR: 'Operador', DIRECTIVO_JASS: 'Directivo' }

function Miembro({ m }) {
  return (
    <li className="flex items-center justify-between gap-3 py-1.5">
      <span className="flex items-center gap-2 min-w-0">
        <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${m.activo ? 'bg-verde' : 'bg-slate-300'}`} />
        <span className="truncate text-slate-700">{m.nombres}</span>
      </span>
      <span className="shrink-0 text-xs text-slate-400">
        {ROL[m.rol] || m.rol} · {m.telefono}
      </span>
    </li>
  )
}

/**
 * Alta de una comunidad con su JASS.
 *
 * Se registran a mano porque cada distrito tiene un número distinto de
 * comunidades y no hay padrón oficial del que leerlas. Al crearse nace su
 * junta: la relación es 1:1 y no tiene sentido una comunidad sin JASS.
 */
function AltaComunidad({ ubigeos, onCreada, onCancelar }) {
  const [f, setF] = useState({ nombre: '', jass_nombre: '', poblacion_servida: '', ubigeo_id: '' })
  const [error, setError] = useState('')
  const [guardando, setGuardando] = useState(false)

  const unico = ubigeos.length === 1 ? ubigeos[0] : null
  const ubigeoId = unico ? unico.ubigeo_id : f.ubigeo_id

  // El nombre de la junta acompaña al de la comunidad mientras no se toque.
  function ponerNombre(nombre) {
    const sugerido = `JASS ${nombre}`.trim()
    const seguia = f.jass_nombre === `JASS ${f.nombre}`.trim() || f.jass_nombre === ''
    setF({ ...f, nombre, jass_nombre: seguia ? sugerido : f.jass_nombre })
  }

  async function enviar(e) {
    e.preventDefault()
    if (!ubigeoId) return setError('Elija el distrito al que pertenece.')
    setError('')
    setGuardando(true)
    try {
      await api.crearComunidad({
        ubigeo_id: Number(ubigeoId),
        nombre: f.nombre.trim(),
        jass_nombre: f.jass_nombre.trim() || null,
        poblacion_servida: f.poblacion_servida ? Number(f.poblacion_servida) : null,
      })
      onCreada()
    } catch (err) {
      setError(err.message)
    } finally {
      setGuardando(false)
    }
  }

  return (
    <form onSubmit={enviar} className="card">
      <h2 className="font-semibold text-agua-800">Registrar comunidad</h2>
      <p className="mt-1 text-sm text-slate-500">
        {unico
          ? `Se registrará en ${unico.provincia} · ${unico.distrito}.`
          : 'Elija la provincia y el distrito al que pertenece.'}
      </p>

      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {!unico && (
          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Distrito
            </span>
            <select className="input mt-1" value={f.ubigeo_id}
              onChange={(e) => setF({ ...f, ubigeo_id: e.target.value })} required>
              <option value="">Seleccione…</option>
              {ubigeos.map((u) => (
                <option key={u.ubigeo_id} value={u.ubigeo_id}>
                  {u.provincia} · {u.distrito}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Comunidad
          </span>
          <input className="input mt-1" value={f.nombre}
            onChange={(e) => ponerNombre(e.target.value)}
            placeholder="Comunidad 04" required />
        </label>

        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Su JASS
          </span>
          <input className="input mt-1" value={f.jass_nombre}
            onChange={(e) => setF({ ...f, jass_nombre: e.target.value })}
            placeholder="JASS Comunidad 04" />
        </label>

        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Población servida
          </span>
          <input className="input mt-1" type="number" min="0" value={f.poblacion_servida}
            onChange={(e) => setF({ ...f, poblacion_servida: e.target.value })}
            placeholder="320" />
        </label>
      </div>

      {error && <p className="mt-4 text-sm text-rojo bg-rojo/10 rounded-lg px-3 py-2">{error}</p>}

      <div className="mt-5 flex gap-3">
        <button className="btn-primary" disabled={guardando}>
          {guardando ? 'Registrando…' : 'Registrar comunidad'}
        </button>
        <button type="button" className="btn-ghost" onClick={onCancelar}>Cancelar</button>
      </div>
    </form>
  )
}

/** Alta de un reservorio dentro de la comunidad que ya se está mirando. */
function AltaReservorio({ jass, onCreado, onCancelar }) {
  const [f, setF] = useState({ codigo: '', volumen_m3: '', tipo_sistema: 'Gravedad' })
  const [error, setError] = useState('')
  const [guardando, setGuardando] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    setError('')
    setGuardando(true)
    try {
      await api.crearReservorio({
        comunidad_id: jass.comunidad_id,
        codigo: f.codigo.trim(),
        volumen_m3: Number(f.volumen_m3),
        tipo_sistema: f.tipo_sistema,
        estado_infra: 'Operativo',
        umbral_silencio_dias: 7,
      })
      onCreado()
    } catch (err) {
      setError(err.message)
    } finally {
      setGuardando(false)
    }
  }

  return (
    <form onSubmit={enviar} className="mt-4 border-t border-slate-100 pt-4 space-y-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        Nuevo reservorio en {jass.comunidad}
      </p>
      <input className="input" value={f.codigo} required
        onChange={(e) => setF({ ...f, codigo: e.target.value })}
        placeholder="Código, p. ej. R4 - LIRCAY - COM - 04" />
      <div className="grid grid-cols-2 gap-3">
        <input className="input" type="number" step="0.1" min="0" required
          value={f.volumen_m3} onChange={(e) => setF({ ...f, volumen_m3: e.target.value })}
          placeholder="Volumen m³" />
        <select className="input" value={f.tipo_sistema}
          onChange={(e) => setF({ ...f, tipo_sistema: e.target.value })}>
          <option>Gravedad</option>
          <option>Bombeo</option>
          <option>Mixto</option>
        </select>
      </div>
      {error && <p className="text-sm text-rojo bg-rojo/10 rounded px-3 py-2">{error}</p>}
      <div className="flex gap-2">
        <button className="btn-primary" disabled={guardando}>
          {guardando ? 'Registrando…' : 'Registrar'}
        </button>
        <button type="button" className="btn-ghost" onClick={onCancelar}>Cancelar</button>
      </div>
    </form>
  )
}

function TarjetaJass({ j, puedeAdministrar, onCambio }) {
  const [creandoReservorio, setCreandoReservorio] = useState(false)
  const sinOperador = !j.miembros.some((m) => m.rol === 'OPERADOR')

  return (
    <article className="card flex flex-col">
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-semibold text-agua-800 truncate">{j.jass_nombre}</h3>
          <p className="text-xs text-slate-500">
            {j.comunidad}
            {j.poblacion_servida ? ` · ${j.poblacion_servida} habitantes` : ''}
          </p>
        </div>
        <NivelBadge nivel={j.nivel} />
      </header>

      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-xs text-slate-400">Reservorios</dt>
          <dd className="font-medium text-slate-700">{j.reservorios}</dd>
        </div>
        <div>
          <dt className="text-xs text-slate-400">Último reporte</dt>
          <dd className={`font-medium ${j.en_silencio ? 'text-rojo' : 'text-slate-700'}`}>
            {j.dias_sin_medir === null
              ? 'Nunca'
              : j.dias_sin_medir === 0
                ? 'Hoy'
                : `Hace ${j.dias_sin_medir} d`}
          </dd>
        </div>
      </dl>

      <div className="mt-4 border-t border-slate-100 pt-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          Integrantes
        </p>
        {j.miembros.length === 0 ? (
          <p className="mt-2 text-sm text-slate-400">Sin personas registradas.</p>
        ) : (
          <ul className="mt-1 divide-y divide-slate-50">
            {j.miembros.map((m) => <Miembro key={m.usuario_id} m={m} />)}
          </ul>
        )}
      </div>

      {(j.en_silencio || sinOperador || j.reservorios === 0) && (
        <ul className="mt-4 space-y-1 text-xs text-amarillo">
          {j.reservorios === 0 && <li>⚠ Sin reservorio: no hay qué medir todavía.</li>}
          {sinOperador && <li>⚠ Sin operador: nadie puede medir el reservorio.</li>}
          {j.en_silencio && j.reservorios > 0 && (
            <li>⚠ No reporta hace más días de los previstos.</li>
          )}
        </ul>
      )}

      {puedeAdministrar && (creandoReservorio ? (
        <AltaReservorio jass={j}
          onCancelar={() => setCreandoReservorio(false)}
          onCreado={() => { setCreandoReservorio(false); onCambio() }} />
      ) : (
        <button className="mt-4 self-start text-sm text-agua-700 hover:underline"
          onClick={() => setCreandoReservorio(true)}>
          + Registrar reservorio
        </button>
      ))}
    </article>
  )
}

export default function Jass() {
  const { user } = useAuth()
  // La ATM administra su distrito; el ADMIN, toda la región.
  const puedeAdministrar = ['ATM', 'ADMIN'].includes(user?.rol)

  const [jass, setJass] = useState(null)
  const [ubigeos, setUbigeos] = useState([])
  const [creando, setCreando] = useState(false)
  const [error, setError] = useState('')

  function cargar() {
    api.jass().then(setJass).catch((e) => setError(e.message))
  }

  useEffect(() => {
    cargar()
    if (puedeAdministrar) api.ubigeos().then(setUbigeos).catch(() => setUbigeos([]))
  }, [puedeAdministrar])

  if (error) return <div className="card text-rojo">{error}</div>
  if (!jass) return <Spinner texto="Cargando el directorio de JASS…" />

  const enSilencio = jass.filter((j) => j.en_silencio).length
  const enRojo = jass.filter((j) => j.nivel === 'ROJO').length
  const poblacion = jass.reduce((t, j) => t + (j.poblacion_servida || 0), 0)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-agua-800">JASS del distrito</h1>
          <p className="text-sm text-slate-500">
            Cada comunidad tiene su propia junta; usted las acompaña a todas.
          </p>
        </div>
        {puedeAdministrar && !creando && (
          <button className="btn-primary" onClick={() => setCreando(true)}>
            + Registrar comunidad
          </button>
        )}
      </div>

      {creando && (
        <AltaComunidad ubigeos={ubigeos}
          onCancelar={() => setCreando(false)}
          onCreada={() => { setCreando(false); cargar() }} />
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Juntas" value={jass.length} />
        <StatCard label="Población servida" value={poblacion.toLocaleString('es-PE')} />
        <StatCard label="Agua no segura" value={enRojo} accent="rojo" />
        <StatCard label="Sin reportar" value={enSilencio} accent="amarillo" />
      </div>

      {jass.length === 0 ? (
        <div className="card text-slate-500">
          Su distrito aún no tiene comunidades registradas. Regístrelas una por una:
          cada comunidad trae su propia JASS.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {jass.map((j) => (
            <TarjetaJass key={j.comunidad_id} j={j}
              puedeAdministrar={puedeAdministrar} onCambio={cargar} />
          ))}
        </div>
      )}
    </div>
  )
}

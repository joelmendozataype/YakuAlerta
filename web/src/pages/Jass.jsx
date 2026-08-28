import { useEffect, useState } from 'react'
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

function TarjetaJass({ j }) {
  const sinDirectivo = !j.miembros.some((m) => m.rol === 'DIRECTIVO_JASS')
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

      {(j.en_silencio || sinDirectivo || sinOperador) && (
        <ul className="mt-4 space-y-1 text-xs text-amarillo">
          {j.en_silencio && <li>⚠ No reporta hace más días de los previstos.</li>}
          {sinOperador && <li>⚠ Sin operador: nadie puede medir el reservorio.</li>}
          {sinDirectivo && <li>⚠ Sin directivo registrado.</li>}
        </ul>
      )}
    </article>
  )
}

export default function Jass() {
  const [jass, setJass] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.jass().then(setJass).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="card text-rojo">{error}</div>
  if (!jass) return <Spinner texto="Cargando el directorio de JASS…" />

  const enSilencio = jass.filter((j) => j.en_silencio).length
  const enRojo = jass.filter((j) => j.nivel === 'ROJO').length
  const poblacion = jass.reduce((t, j) => t + (j.poblacion_servida || 0), 0)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-agua-800">JASS del distrito</h1>
        <p className="text-sm text-slate-500">
          Cada comunidad tiene su propia junta; usted las acompaña a todas.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Juntas" value={jass.length} />
        <StatCard label="Población servida" value={poblacion.toLocaleString('es-PE')} />
        <StatCard label="Agua no segura" value={enRojo} accent="rojo" />
        <StatCard label="Sin reportar" value={enSilencio} accent="amarillo" />
      </div>

      {jass.length === 0 ? (
        <div className="card text-slate-500">
          Su distrito aún no tiene comunidades registradas.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {jass.map((j) => <TarjetaJass key={j.comunidad_id} j={j} />)}
        </div>
      )}
    </div>
  )
}

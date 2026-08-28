import { useEffect, useState } from 'react'
import { api } from '../api'

/**
 * Los siete actores del sistema, con la superficie por la que entra cada uno.
 *
 * El catálogo lo declara el backend a partir de la misma constante que
 * gobierna las dos pantallas de ingreso: si mañana un actor cambia de
 * superficie, esta tabla cambia sola en vez de quedar mintiendo.
 */

function Donde({ movil, tablero }) {
  const partes = [
    movil && { texto: 'Móvil', clase: 'bg-agua-100 text-agua-800' },
    tablero && { texto: 'Web', clase: 'bg-slate-200 text-slate-700' },
  ].filter(Boolean)

  return (
    <span className="inline-flex items-center gap-1.5">
      {partes.map((p, i) => (
        <span key={p.texto} className="inline-flex items-center gap-1.5">
          {i > 0 && <span className="text-slate-300">+</span>}
          <span className={`badge ${p.clase}`}>{p.texto}</span>
        </span>
      ))}
    </span>
  )
}

export default function Actores() {
  const [actores, setActores] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.actores().then(setActores).catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="card text-rojo">{error}</div>
  if (!actores) return null

  const enMovil = actores.filter((a) => a.movil).length
  const enWeb = actores.filter((a) => a.tablero).length
  const enAmbas = actores.filter((a) => a.movil && a.tablero).length

  return (
    <section className="card p-0 overflow-hidden">
      <header className="px-5 pt-5">
        <h2 className="font-semibold text-agua-800">Actores del sistema</h2>
        <p className="text-sm text-slate-500">
          {actores.length} actores · {enMovil} en la app, {enWeb} en el tablero,{' '}
          {enAmbas} en ambas
        </p>
      </header>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-5 py-3 font-semibold w-10">#</th>
              <th className="px-4 py-3 font-semibold">Actor</th>
              <th className="px-4 py-3 font-semibold">Dónde entra</th>
              <th className="px-4 py-3 font-semibold text-right">Cuentas</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {actores.map((a) => (
              <tr key={a.grupo}>
                <td className="px-5 py-3 text-slate-400">{a.orden}</td>
                <td className="px-4 py-3">
                  <p className="font-medium text-slate-800">{a.actor}</p>
                </td>
                <td className="px-4 py-3">
                  <Donde movil={a.movil} tablero={a.tablero} />
                </td>
                <td className="px-4 py-3 text-right">
                  {a.cuentas === 0 ? (
                    <span className="text-sm text-slate-300">—</span>
                  ) : (
                    <span className="text-sm text-slate-600">
                      {a.activas}
                      {a.activas !== a.cuentas && (
                        <span className="text-slate-400"> de {a.cuentas}</span>
                      )}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

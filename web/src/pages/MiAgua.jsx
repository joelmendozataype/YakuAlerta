import { useEffect, useState } from 'react'
import { useAuth } from '../auth'
import { api } from '../api'
import { Spinner } from '../components/ui'

const COLOR = {
  VERDE: 'bg-verde',
  AMARILLO: 'bg-amarillo',
  ROJO: 'bg-rojo',
}

/**
 * Vista para una cuenta de población que abre el tablero desde su celular.
 *
 * Responde una sola pregunta —¿puedo tomar el agua hoy?— en lenguaje llano y
 * sin valores técnicos, igual que la app y el aviso comunitario impreso. No
 * muestra el tablero institucional, que no es su ámbito.
 */
export default function MiAgua() {
  const { user } = useAuth()
  const [estado, setEstado] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user?.comunidad_id) {
      setError('Tu cuenta aún no tiene una comunidad asignada. Solicita a la ATM que la registre.')
      return
    }
    api.estadoPublico(user.comunidad_id)
      .then(setEstado)
      .catch((e) => setError(e.message))
  }, [user])

  if (error) {
    return (
      <div className="card max-w-xl mx-auto text-center text-slate-600">{error}</div>
    )
  }
  if (!estado) return <Spinner texto="Consultando el estado del agua…" />

  return (
    <div className="max-w-xl mx-auto">
      <div className={`rounded-2xl text-white text-center p-8 ${COLOR[estado.nivel] || 'bg-slate-400'}`}>
        <div className="text-5xl">💧</div>
        <h1 className="mt-3 text-3xl font-bold">{estado.etiqueta}</h1>
        <p className="mt-1 text-white/90">
          {estado.comunidad} · {estado.distrito}
        </p>
        <p className="mt-4 text-lg font-medium">{estado.instruccion}</p>
      </div>

      <div className="card mt-6">
        <h2 className="font-semibold text-agua-800 mb-3">¿Qué debe hacer?</h2>
        <ul className="space-y-2 text-slate-700">
          {estado.acciones.map((a, i) => (
            <li key={i} className="flex gap-3">
              <span className={`mt-2 h-2 w-2 rounded-full shrink-0 ${COLOR[estado.nivel] || 'bg-slate-400'}`} />
              <span>{a}</span>
            </li>
          ))}
        </ul>
      </div>

      <p className="text-center text-xs text-slate-400 mt-6">
        Información difundida por su JASS con apoyo del Área Técnica Municipal
      </p>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { useAuth } from '../auth'
import { api } from '../api'
import { Spinner } from '../components/ui'

/**
 * Umbrales normativos con los que se clasifica cada medición (RNF-07).
 *
 * No están escritos en el código: si cambia el D.S., el ADMIN los ajusta aquí
 * y rige de inmediato, sin recompilar ni redesplegar. Las demás instituciones
 * los consultan —necesitan saber con qué regla se clasificó lo que firman—
 * pero no los mueven: un umbral distinto por distrito rompería la
 * comparabilidad del dato y su defensa legal.
 */

// Cómo se lee cada parámetro, para que nadie invierta los umbrales sin darse
// cuenta de lo que significan.
// El verde no tiene campo propio: es la banda que queda cuando el valor no
// cruza el amarillo. La pantalla lo dejaba implícito y había que deducirlo.
const SENTIDO = {
  cloro_residual: {
    titulo: 'Cloro residual libre',
    explica: 'Es el desinfectante que queda en el agua. Menos cloro es más riesgo, '
      + 'así que el umbral rojo va por debajo del amarillo.',
    amarillo: 'Por debajo de este valor, el agua entra en riesgo',
    rojo: 'Por debajo de este valor, el agua no es segura',
    bandas: (a, r) => [
      ['VERDE', `≥ ${a}`],
      ['AMARILLO', `${r} – ${a}`],
      ['ROJO', `< ${r}`],
    ],
  },
  turbidez: {
    titulo: 'Turbidez',
    explica: 'Son las partículas suspendidas que enturbian el agua. Más turbidez es '
      + 'más riesgo, así que el umbral rojo va por encima del amarillo.',
    amarillo: 'Por encima de este valor, el agua entra en riesgo',
    rojo: 'Por encima de este valor, el agua no es segura',
    bandas: (a, r) => [
      ['VERDE', `≤ ${a}`],
      ['AMARILLO', `${a} – ${r}`],
      ['ROJO', `> ${r}`],
    ],
  },
}

const COLOR_BANDA = {
  VERDE: { punto: 'bg-verde', texto: 'text-verde', rotulo: 'Segura' },
  AMARILLO: { punto: 'bg-amarillo', texto: 'text-amarillo', rotulo: 'En riesgo' },
  ROJO: { punto: 'bg-rojo', texto: 'text-rojo', rotulo: 'No segura' },
}

/** Las tres bandas resultantes, para ver el efecto antes de guardar. */
function Bandas({ info, amarillo, rojo }) {
  if (!info.bandas || amarillo === '' || rojo === '') return null
  return (
    <div className="mt-5 grid grid-cols-3 gap-2 rounded-lg bg-slate-50 p-3">
      {info.bandas(amarillo, rojo).map(([nivel, rango]) => {
        const c = COLOR_BANDA[nivel]
        return (
          <div key={nivel} className="text-center">
            <span className={`mx-auto block h-2.5 w-2.5 rounded-full ${c.punto}`} />
            <p className={`mt-1.5 text-sm font-semibold ${c.texto}`}>{rango}</p>
            <p className="text-[11px] text-slate-400">{c.rotulo}</p>
          </div>
        )
      })}
    </div>
  )
}

function Tarjeta({ p, editable, onGuardado, onError }) {
  const [amarillo, setAmarillo] = useState(p.umbral_amarillo ?? '')
  const [rojo, setRojo] = useState(p.umbral_rojo ?? '')
  const [guardando, setGuardando] = useState(false)
  const [guardado, setGuardado] = useState(false)

  const info = SENTIDO[p.parametro] || {
    titulo: p.parametro, explica: '', amarillo: 'Umbral amarillo', rojo: 'Umbral rojo',
  }
  const cambio = String(amarillo) !== String(p.umbral_amarillo ?? '')
    || String(rojo) !== String(p.umbral_rojo ?? '')

  async function guardar() {
    setGuardando(true)
    setGuardado(false)
    onError('')
    try {
      await api.corregirParametro(p.parametro_id, {
        umbral_amarillo: amarillo === '' ? null : Number(amarillo),
        umbral_rojo: rojo === '' ? null : Number(rojo),
      })
      setGuardado(true)
      onGuardado()
    } catch (e) {
      onError(e.message)
    } finally {
      setGuardando(false)
    }
  }

  function descartar() {
    setAmarillo(p.umbral_amarillo ?? '')
    setRojo(p.umbral_rojo ?? '')
    setGuardado(false)
    onError('')
  }

  return (
    <article className="card">
      <header className="flex items-baseline justify-between gap-3">
        <h2 className="font-semibold text-agua-800">{info.titulo}</h2>
        <span className="text-xs text-slate-400">{p.unidad}</span>
      </header>
      {info.explica && <p className="mt-2 text-sm text-slate-500">{info.explica}</p>}

      <div className="mt-5 space-y-4">
        <label className="block">
          <span className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <span className="h-2.5 w-2.5 rounded-full bg-amarillo" />
            Umbral amarillo
          </span>
          <input className="input mt-1" type="number" step="0.01" min="0"
            value={amarillo} disabled={!editable}
            onChange={(e) => setAmarillo(e.target.value)} />
          <span className="mt-1 block text-xs text-slate-400">{info.amarillo}</span>
        </label>

        <label className="block">
          <span className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <span className="h-2.5 w-2.5 rounded-full bg-rojo" />
            Umbral rojo
          </span>
          <input className="input mt-1" type="number" step="0.01" min="0"
            value={rojo} disabled={!editable}
            onChange={(e) => setRojo(e.target.value)} />
          <span className="mt-1 block text-xs text-slate-400">{info.rojo}</span>
        </label>
      </div>

      <Bandas info={info} amarillo={amarillo} rojo={rojo} />

      <p className="mt-4 text-xs text-slate-400">Norma: {p.norma_referencia}</p>

      {editable && cambio && (
        <div className="mt-4 flex gap-3">
          <button className="btn-primary" onClick={guardar} disabled={guardando}>
            {guardando ? 'Guardando…' : 'Guardar'}
          </button>
          <button className="btn-ghost" onClick={descartar} disabled={guardando}>
            Descartar
          </button>
        </div>
      )}
      {guardado && !cambio && (
        <p className="mt-4 text-sm text-verde">
          Guardado. Rige para las mediciones que lleguen desde ahora.
        </p>
      )}
    </article>
  )
}

export default function Parametros() {
  const { user } = useAuth()
  const editable = user?.rol === 'ADMIN'

  const [params, setParams] = useState(null)
  const [error, setError] = useState('')

  function cargar() {
    api.parametros().then(setParams).catch((e) => setError(e.message))
  }

  useEffect(cargar, [])

  if (!params) return <Spinner texto="Cargando los umbrales normativos…" />

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-agua-800">Umbrales normativos</h1>
        <p className="text-sm text-slate-500">
          Con estos valores el sistema decide si el agua de una comunidad es segura.
        </p>
      </div>

      {!editable && (
        <div className="card bg-slate-50 text-sm text-slate-600">
          Usted consulta estos umbrales, pero no los modifica. Un cambio de norma rige
          para toda la región y lo aplica la administración del sistema.
        </div>
      )}

      {error && <div className="card text-rojo">{error}</div>}

      <div className="grid gap-4 md:grid-cols-2">
        {params.map((p) => (
          <Tarjeta key={p.parametro_id} p={p} editable={editable}
            onGuardado={cargar} onError={setError} />
        ))}
      </div>

      <p className="text-xs text-slate-400">
        Cada cambio queda registrado en auditoría con su valor anterior: sin ese rastro
        no se podría explicar por qué una comunidad cambió de color sin que cambiara su agua.
      </p>
    </div>
  )
}

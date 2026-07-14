// Cliente REST mínimo para la API de YakuAlerta.
const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function getToken() {
  return localStorage.getItem('yaku_token')
}

async function request(path, { method = 'GET', body, blob = false } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  if (res.status === 401) {
    localStorage.removeItem('yaku_token')
    localStorage.removeItem('yaku_user')
    window.location.href = '/login'
    throw new Error('Sesión expirada')
  }
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail } catch { /* ignore */ }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  if (blob) return res.blob()
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  base: BASE,
  login: (telefono, clave) => request('/auth/login', { method: 'POST', body: { telefono, clave } }),
  distritos: () => request('/tablero/distritos'),
  tablero: (ubigeoId) => request(`/tablero/${ubigeoId}`),
  historial: (reservorioId) => request(`/tablero/reservorio/${reservorioId}/historial`),
  alertas: (estado = 'ACTIVA') => request(`/alertas?estado=${estado}`),
  alerta: (id) => request(`/alertas/${id}`),
  cerrarAlerta: (id, payload) => request(`/alertas/${id}/cerrar`, { method: 'POST', body: payload }),
  silencio: () => request('/reportes/silencio'),
  registrarLab: (payload) => request('/laboratorio', { method: 'POST', body: payload }),
  labReservorio: (id) => request(`/laboratorio/reservorio/${id}`),
  mediciones: (reservorioId) => request(`/mediciones?reservorio_id=${reservorioId}`),
  reporteUrl: (ubigeoId, periodo, formato) =>
    `${BASE}/reportes/vigilancia?ubigeo_id=${ubigeoId}&periodo=${periodo}&formato=${formato}`,
  descargarReporte: (ubigeoId, periodo, formato) =>
    request(`/reportes/vigilancia?ubigeo_id=${ubigeoId}&periodo=${periodo}&formato=${formato}`, { blob: true }),
}

export { getToken }

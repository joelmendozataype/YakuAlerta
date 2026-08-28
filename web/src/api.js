// Cliente REST mínimo para la API de Yakuni.
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
  login: (dni, clave, grupoRol) =>
    request('/auth/login', { method: 'POST', body: { dni, clave, grupo_rol: grupoRol } }),
  // ─── Inicio de sesión por QR (vinculación con la app) ───────
  qrNueva: (clientHash) => request('/auth/qr/nueva', { method: 'POST', body: { client_hash: clientHash } }),
  qrEstado: (token) => request(`/auth/qr/${token}`),
  qrReclamar: (token, clientSecret) =>
    request(`/auth/qr/${token}/reclamar`, { method: 'POST', body: { client_secret: clientSecret } }),
  distritos: () => request('/tablero/distritos'),
  tablero: (ubigeoId) => request(`/tablero/${ubigeoId}`),
  historial: (reservorioId) => request(`/tablero/reservorio/${reservorioId}/historial`),
  alertas: (estado = 'ACTIVA') => request(`/alertas?estado=${estado}`),
  alerta: (id) => request(`/alertas/${id}`),
  cerrarAlerta: (id, payload) => request(`/alertas/${id}/cerrar`, { method: 'POST', body: payload }),
  silencio: () => request('/reportes/silencio'),
  // Directorio de JASS del distrito (una junta por comunidad).
  jass: () => request('/admin/jass'),
  // Padrón de cuentas: la ATM administra su distrito; el ADMIN, la región.
  // Los siete actores del sistema y donde entra cada uno.
  actores: () => request('/admin/actores'),
  usuarios: () => request('/admin/usuarios'),
  crearUsuario: (payload) => request('/admin/usuarios', { method: 'POST', body: payload }),
  corregirUsuario: (id, payload) =>
    request(`/admin/usuarios/${id}`, { method: 'PATCH', body: payload }),
  restablecerClave: (id) =>
    request(`/admin/usuarios/${id}/clave`, { method: 'POST' }),
  comunidades: () => request('/admin/comunidades'),
  // Umbrales normativos (RNF-07): los mueve solo el ADMIN.
  parametros: () => request('/parametros'),
  corregirParametro: (id, payload) =>
    request(`/parametros/${id}`, { method: 'PATCH', body: payload }),
  // Afiche comunitario imprimible con QR (para fijar en el punto de agua)
  avisoComunitario: (comunidadId) =>
    request(`/avisos/comunidad/${comunidadId}`, { blob: true }),
  // Trae la imagen de evidencia autenticada y devuelve un object URL para <img>.
  evidenciaObjectUrl: async (id) => {
    const blob = await request(`/evidencias/${id}`, { blob: true })
    return URL.createObjectURL(blob)
  },
  registrarLab: (payload) => request('/laboratorio', { method: 'POST', body: payload }),
  labReservorio: (id) => request(`/laboratorio/reservorio/${id}`),
  mediciones: (reservorioId) => request(`/mediciones?reservorio_id=${reservorioId}`),
  reporteUrl: (ubigeoId, periodo, formato) =>
    `${BASE}/reportes/vigilancia?ubigeo_id=${ubigeoId}&periodo=${periodo}&formato=${formato}`,
  descargarReporte: (ubigeoId, periodo, formato) =>
    request(`/reportes/vigilancia?ubigeo_id=${ubigeoId}&periodo=${periodo}&formato=${formato}`, { blob: true }),
}

export { getToken }

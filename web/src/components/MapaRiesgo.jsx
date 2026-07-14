import { MapContainer, TileLayer, CircleMarker, Tooltip } from 'react-leaflet'

const COLOR = { VERDE: '#15803d', AMARILLO: '#b45309', ROJO: '#b91c1c' }

export default function MapaRiesgo({ comunidades }) {
  const conCoord = comunidades.filter((c) => c.latitud && c.longitud)
  const centro = conCoord.length
    ? [conCoord[0].latitud, conCoord[0].longitud]
    : [-12.40, -74.87] // Pampas, Tayacaja

  return (
    <div className="h-80 md:h-full min-h-[20rem]">
      <MapContainer center={centro} zoom={12} scrollWheelZoom={false}>
        <TileLayer
          attribution='&copy; OpenStreetMap'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {conCoord.map((c) => (
          <CircleMarker
            key={c.comunidad_id}
            center={[c.latitud, c.longitud]}
            radius={12}
            pathOptions={{
              color: '#fff',
              weight: 2,
              fillColor: COLOR[c.nivel] || '#94a3b8',
              fillOpacity: 0.9,
            }}
          >
            <Tooltip direction="top">
              <div className="text-xs">
                <p className="font-semibold">{c.comunidad}</p>
                <p>Reservorio {c.reservorio_codigo}</p>
                <p>Nivel: {c.nivel || 'sin dato'}</p>
                {c.silencio && <p className="text-amber-600">⏰ Silencio de datos</p>}
              </div>
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  )
}

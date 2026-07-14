# 💧 YakuAlerta

**Sistema de alerta temprana para agua no segura en reservorios comunales de Huancavelica.**
Hackathon *Kuska Wiñasun: Agua Segura para Huancavelica* — UNH 2026.

YakuAlerta digitaliza el primer eslabón de la vigilancia sanitaria del agua rural: el
operador de la JASS registra la medición de cloro residual y turbidez **sin internet**, el
sistema clasifica automáticamente el riesgo (semáforo 🟢🟡🔴) conforme al **D.S. N.° 031-2010-SA**,
emite **alertas accionables por SMS/WhatsApp** y consolida todo en un **tablero institucional**
para la ATM y la DIRESA/DESA.

## Arquitectura (3 capas)

| Capa | Stack | Carpeta |
|------|-------|---------|
| 📱 App móvil (operador JASS) | Flutter · Dart · SQLite (offline-first) | [`mobile/`](mobile/) |
| ⚙️ Backend + motor de reglas | Python · FastAPI · PostgreSQL/PostGIS · Redis | [`backend/`](backend/) |
| 🖥️ Tablero web institucional | React · Vite · Tailwind · Leaflet · Recharts | [`web/`](web/) |

```
                 SMS / 2G  ┌───────────────┐   REST/HTTPS   ┌──────────────┐
 [ Operador ]  ─────────▶  │   Backend     │  ◀───────────  │  Tablero web │
 App Flutter   sync/datos  │  FastAPI +    │                │  React (ATM/ │
 (offline)     ─────────▶  │  motor reglas │  ──▶ SMS/WA    │  DESA/salud) │
                           │  PostgreSQL   │   notificación  └──────────────┘
                           └───────────────┘
```

## El motor de reglas (corazón del sistema)

Clasificación por **regla de peor caso** (D.S. N.° 031-2010-SA):

| Nivel | Regla |
|-------|-------|
| 🟢 **VERDE** (segura)     | cloro ≥ 0.50 mg/L **y** turbidez ≤ 5 UNT |
| 🟡 **AMARILLO** (en riesgo) | cloro 0.30–0.49 mg/L |
| 🔴 **ROJO** (no segura)   | cloro < 0.30 mg/L **o** turbidez > 5 UNT **o** observación crítica **o** laboratorio no conforme |

Los umbrales **no están en el código**: viven en la tabla `parametro_normativo` (RNF-07).

## Puesta en marcha rápida

```bash
# 1. Backend + base de datos + tablero web (todo en Docker)
cp .env.example .env
docker compose up --build

#   API      → http://localhost:8000  (Swagger en /docs)
#   Tablero  → http://localhost:5173
#   Login demo (tablero):  atm.pazos  /  yaku2026

# 2. App móvil (requiere Flutter SDK)
cd mobile && flutter pub get && flutter run
```

Ver [`docs/PUESTA_EN_MARCHA.md`](docs/PUESTA_EN_MARCHA.md) para el detalle.

## Mapa de historias de usuario → código

| HU | Funcionalidad | Dónde |
|----|---------------|-------|
| HU-01 | Autenticación por roles | `backend/app/routers/auth.py`, `mobile/lib/features/auth` |
| HU-02 | Registro offline de mediciones | `mobile/lib/features/medicion`, `backend/app/routers/mediciones.py` |
| HU-03 | Clasificación y semáforo | `backend/app/rules/motor_riesgo.py`, `mobile/lib/core/rules` |
| HU-04 | Gestión de entidades | `backend/app/routers/admin.py` |
| HU-05 | Lectura DPD por cámara | `mobile/lib/features/camara_dpd` |
| HU-06 | Recomendación y dosis | `backend/app/rules/dosis.py` |
| HU-07 | Recordatorios de medición | `mobile/lib/features/recordatorios` |
| HU-08 | Evidencia georreferenciada | `mobile/lib/features/evidencia` |
| HU-09/10 | Alertas SMS/WhatsApp + escalamiento | `backend/app/rules/escalamiento.py`, `backend/app/services/notificaciones.py` |
| HU-11 | Canal SMS estructurado | `backend/app/routers/sync.py` (`parse_sms`) |
| HU-12 | Sincronización + deduplicación | `backend/app/routers/sync.py`, `mobile/lib/core/sync` |
| HU-13/14 | Tablero + bandeja de alertas | `web/src/pages` |
| HU-15 | Silencio de datos | `backend/app/services/silencio.py` |
| HU-16 | Cierre de alertas con evidencia | `backend/app/routers/alertas.py` |
| HU-17 | Reportes PDF/Excel | `backend/app/services/reportes.py` |
| HU-18 | Resultados de laboratorio | `backend/app/routers/laboratorio.py` |

## Licencia

Software libre / código abierto (MVP de la hackathon). MIT.

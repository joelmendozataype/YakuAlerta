# 🏗️ Arquitectura de YakuAlerta

## Visión general (offline-first, tres capas)

```
┌──────────────────────────┐        ┌────────────────────────────────┐
│  CAPTURA (campo)          │        │  PLATAFORMA (backend)          │
│  App Flutter              │        │  FastAPI + motor de reglas     │
│  • SQLite (offline)       │  REST  │  • /auth /sync /mediciones     │
│  • motor de reglas local  │──────▶ │  • /alertas /tablero /reportes │
│  • cola de sincronización │  HTTPS │  • /laboratorio                │
│  • cámara DPD, GPS        │        │  PostgreSQL 16 + PostGIS       │
└──────────┬───────────────┘        │  Redis (tareas)                │
           │ SMS 2G (respaldo)      └───────────────┬────────────────┘
           ▼                                        │ SMS/WhatsApp (Twilio)
   ┌────────────────┐                               ▼
   │ Pasarela SMS   │                     ┌────────────────────┐
   │ /sync/sms      │                     │ Destinatarios:     │
   └────────────────┘                     │ operador, ATM,     │
                                          │ JASS, salud        │
   ┌────────────────────────────┐         └────────────────────┘
   │ PRESENTACIÓN institucional │
   │ React + Vite + Tailwind    │  REST   ▲
   │ Leaflet (mapa) · Recharts  │─────────┘
   │ ATM / DIRESA-DESA / salud  │
   └────────────────────────────┘
```

## Principio de diseño: el motor de reglas vive en dos lugares

La clasificación de riesgo se implementa **idéntica** en Python
(`backend/app/rules/motor_riesgo.py`) y en Dart
(`mobile/lib/core/rules/motor_riesgo.dart`). Así el operador ve el semáforo al
instante sin conexión (RNF-04), y el backend re-clasifica de forma autoritativa
al sincronizar, incorporando información que el móvil no tiene (p. ej. un
resultado de laboratorio NO CONFORME que fuerza rojo, RF-15).

Los **umbrales no están en el código** (RNF-07): residen en la tabla
`parametro_normativo` y se inyectan al motor. Cambiar un límite regulatorio no
requiere recompilar.

## Flujo medición → clasificación → alerta → cierre

```
Operador registra medición (offline)
        │  motor local clasifica  🟢/🟡/🔴
        ▼
Se guarda en SQLite (estado PENDIENTE)
        │  al recuperar red → POST /sync (lote comprimido)
        ▼
Backend deduplica por UUID  ──►  re-clasifica  ──►  calcula dosis
        │                                              │
        │  si 🟡/🔴                                     ▼
        ▼                                    crea RECOMENDACION_DOSIS
   crea ALERTA (ACTIVA)
        │  matriz de escalamiento
        ▼
   NOTIFICACION por rol/canal (SMS/WhatsApp)   ← 🟢 nunca notifica (antifatiga)
        │
        ▼
   ATM ve la alerta en el tablero → registra CIERRE con evidencia
        │  regla: rojo solo cierra con remedición VERDE o dictamen DESA
        ▼
   ALERTA CERRADA  (trazabilidad detección–acción–verificación)
```

## Modelo de datos

14 tablas en 3NF (ver `backend/db/init.sql` y el documento de modelamiento).
Núcleo: `medicion` (con `uuid_registro` para deduplicación offline y
`estado_sync` para la cola). El territorio se normaliza en
`ubigeo → comunidad → reservorio`. La respuesta al riesgo se traza en
`alerta → notificacion`, y el laboratorio en `resultado_laboratorio`.

## Seguridad (RNF-05, Ley N.° 29733)

- Autenticación JWT por rol, con **mínimo privilegio** (`deps.requiere_roles`).
- Claves con **bcrypt** (nunca en texto plano).
- **Auditoría** de accesos y cambios (`auditoria`).
- TLS en tránsito (Nginx + Let's Encrypt en el despliegue del piloto).

## Resiliencia / contexto rural

| Restricción | Respuesta de diseño |
|-------------|---------------------|
| Sin internet | offline-first: SQLite + cola + sincronización oportunista |
| Solo red 2G | canal SMS estructurado (`YA;RES-001;CL:0.10;TB:8`) |
| Teléfonos de gama baja | Flutter compilado nativo, UI de campos grandes |
| Batería en jornada | GPS solo al capturar la foto (RNF-08) |
| Duplicidad SMS+datos | deduplicación por UUID en el backend |

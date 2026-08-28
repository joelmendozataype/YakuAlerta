# 🚀 Puesta en marcha — Yakuni

## Requisitos

| Herramienta | Versión | Para |
|-------------|---------|------|
| Docker + Docker Compose | reciente | Backend + BD + tablero (todo en uno) |
| Flutter SDK | ≥ 3.19 | App móvil |
| (opcional) Python 3.12 | | Correr el backend sin Docker |
| (opcional) Node 20 | | Correr el tablero sin Docker |

---

## Opción A — Todo con Docker (recomendada)

```bash
cp .env.example .env
docker compose up --build
```

Esto levanta cuatro contenedores:

| Servicio | URL | Notas |
|----------|-----|-------|
| `db` (PostgreSQL 16 + PostGIS) | localhost:5432 | esquema creado por `backend/db/init.sql` |
| `redis` | localhost:6379 | cola de tareas / recordatorios |
| `api` (FastAPI) | http://localhost:8000 · **/docs** | siembra datos demo al arrancar |
| `web` (tablero React) | http://localhost:5173 | |

**Territorio sembrado.** El sistema nace con los doce distritos de la
provincia de **Angaraes (Huancavelica)**, con sus códigos INEI `090201`–`090212`.
Solo **Lircay** arranca con datos; los once restantes esperan a su ATM, de modo
que sumar el segundo distrito no exige tocar la base.

| Departamento | Provincia | Distrito | Comunidad | Reservorio |
|---|---|---|---|---|
| HUANCAVELICA | ANGARAES | LIRCAY | `COM-01` | `R1-LIRCAY-COM-01` |
| HUANCAVELICA | ANGARAES | LIRCAY | `COM-02` | `R2-LIRCAY-COM-02` |
| HUANCAVELICA | ANGARAES | LIRCAY | `COM-03` | `R3-LIRCAY-COM-03` |

Cada comunidad tiene su propia JASS (relación 1:1) y la ATM de Lircay acompaña
a las tres. Las comunidades y sus reservorios se registran a mano desde la
pantalla **JASS**: cada distrito tiene un número distinto y no hay padrón del
que leerlas.

**Login del tablero (demo).** Se elige el actor y se entra con DNI y clave;
la clave de todas las cuentas de demostración es `yaku2026`.

| Actor | DNI | Entra por |
|-------|-----|-----------|
| ATM | `70100020` | app y tablero |
| IPRESS / Salud | `70100040` | app y tablero |
| DESA | `70100030` | tablero |
| DRVCS | `70100070` | tablero |
| Administrador | `70100099` | tablero |
| JASS (operadores) | `70100001` · `70100002` · `70100003` | solo la app móvil |
| Usuario / vecino | `70100060` | solo la app móvil |

La JASS y el vecino no entran al tablero: la primera trabaja en el cerro con el
celular, sin señal; el segundo consulta el estado de su agua escaneando el QR
del aviso fijado en el punto de agua, sin cuenta ni clave.

---

## Opción B — Backend sin Docker, con SQLite (sin instalar base de datos)

La vía más rápida: no instalas ningún servidor de BD, se usa un archivo SQLite.
El `backend/.env` ya viene configurado con `DATABASE_URL=sqlite:///./yakuni.db`.

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python -m app.seed            # crea el esquema + datos demo en yakuni.db
uvicorn app.main:app --reload
```

→ http://localhost:8000/docs · el archivo `yakuni.db` aparece en `backend/`.
Para reiniciar los datos, borra `yakuni.db` y vuelve a correr `app.seed`.

## Opción C — Backend sin Docker, con PostgreSQL

```bash
cd backend
python -m venv .venv && .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Instala PostgreSQL, crea la BD y carga backend/db/init.sql.
# Cambia DATABASE_URL en backend/.env a:
#   postgresql+psycopg://postgres:TU_PASSWORD@localhost:5432/yakuni
python -m app.seed
uvicorn app.main:app --reload
```

Pruebas del motor de reglas y del deduplicador:

```bash
cd backend && pytest          # boundary values 0.29/0.30/0.49/0.50 mg/L; 5/6 UNT
```

---

## Tablero web sin Docker

```bash
cd web
npm install
npm run dev        # http://localhost:5173  (usa VITE_API_URL, por defecto :8000)
```

---

## App móvil

Ver [`mobile/README.md`](../mobile/README.md). Resumen:

```bash
cd mobile
flutter create .       # genera android/ e ios/
flutter pub get
flutter run            # emulador Android; API en http://10.0.2.2:8000
```

---

## Demostración guiada (Demo Day)

1. **Registro offline** (app, en modo avión): mide `cloro 0.10 · turbidez 8` en un
   reservorio → semáforo 🔴 al instante + dosis de recloración + protocolo.
2. **Reconexión**: desactiva el modo avión → la medición se sincroniza sola.
3. **Alerta** (tablero): aparece en la **bandeja de alertas** con su protocolo y
   las notificaciones enviadas (en modo simulado se ven en los logs de `api`).
4. **Cierre trazable**: intenta cerrar la alerta roja sin remedición → **se bloquea**
   (CA-HU16-02). Registra una remedición verde y ciérrala con evidencia.
5. **Silencio de datos**: la comunidad *Huaribamba* no tiene mediciones → aparece
   como silencio en el tablero (HU-15).
6. **Reporte**: en *Reportes*, descarga el consolidado del distrito en PDF/Excel.
7. **Laboratorio**: registra un resultado *NO CONFORME* (DESA) → el reservorio se
   fuerza a 🔴 hasta el cierre sanitario (HU-18).

---

## Verificación de los criterios de aceptación

| Criterio | Cómo probarlo |
|----------|---------------|
| CA-HU03-01/02/03 | `pytest backend/tests/test_motor_riesgo.py` |
| CA-HU06-01 | `pytest backend/tests/test_dosis.py` |
| CA-HU11-01 | `POST /sync/sms` con `YA;RES-001;CL:0.10;TB:8` (Swagger) |
| CA-HU12-02 | Enviar la misma medición por `/sync/sms` y luego por `/sync` → 1 sola fila |
| CA-HU16-02 | `POST /alertas/{id}/cerrar` sin remedición en alerta roja → 422 |
| CA-HU18-01 | `POST /laboratorio` con `dictamen=NO_CONFORME` → reservorio en rojo |

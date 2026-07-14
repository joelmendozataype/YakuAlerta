# 📱 YakuAlerta — App móvil del operador JASS

App **offline-first** en Flutter para el registro de mediciones de calidad del
agua en campo, con clasificación de riesgo local, recomendación de dosis y
sincronización automática (con canal SMS de respaldo).

## Estructura

```
lib/
├── main.dart                     # arranque + auto-sync
├── core/
│   ├── theme.dart                # identidad visual agua/petróleo
│   ├── rules/motor_riesgo.dart   # motor de reglas LOCAL (idéntico al backend)
│   ├── db/local_db.dart          # SQLite offline (sqflite)
│   ├── api/api_client.dart       # cliente REST
│   ├── sync/sync_service.dart    # cola + sincronización + deduplicación
│   └── models/                   # Medicion, Reservorio
└── features/
    ├── auth/login_screen.dart        # HU-01
    ├── home/home_screen.dart         # reservorios, estado offline, cola
    ├── camara_dpd/                   # HU-05 lectura DPD por cámara (análisis HSV)
    ├── evidencia/                    # HU-08 foto georreferenciada
    └── medicion/
        ├── registro_screen.dart      # HU-02 (validación de rangos físicos)
        └── resultado_screen.dart     # HU-03 semáforo + HU-06 dosis

core/vision/dpd_analyzer.dart         # HU-05 estimación de cloro por color (testeable)
core/notificaciones/…                 # HU-07 recordatorios locales
core/evidencia/…                      # HU-08 captura + compresión + GPS
```

## Puesta en marcha

Las carpetas de plataforma (`android/`, `ios/`) no se versionan. Genéralas y
resuelve dependencias:

```bash
cd mobile
flutter create .            # genera android/ e ios/ para este paquete
flutter pub get
flutter test                # pruebas del motor de reglas
flutter run                 # emulador Android de gama baja (Android 8+)
```

- **Backend en el emulador Android:** la app apunta a `http://10.0.2.2:8000`
  (localhost del host). Para un dispositivo físico, pasa la IP de tu PC:
  `flutter run --dart-define=API_URL=http://192.168.x.x:8000`

## Permisos Android requeridos

Tras `flutter create .`, añade a `android/app/src/main/AndroidManifest.xml`
(dentro de `<manifest>`):

```xml
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>  <!-- HU-08 -->
<uses-permission android:name="android.permission.CAMERA"/>                 <!-- HU-05 -->
<uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>     <!-- HU-07 -->
```

Y `minSdkVersion 26` (Android 8) en `android/app/build.gradle` (RNF-03).

## Prueba del modo sin conexión (CA-HU01-02, CA-HU02-01)

1. Inicia sesión una vez con red (la sesión persiste en el dispositivo).
2. Activa el **modo avión**.
3. Registra una medición → se clasifica al instante y se guarda como *pendiente*.
4. Desactiva el modo avión → la cola se sincroniza automáticamente sin duplicar.

# 🤖 Fase 2 — Lectura del comparador DPD con TensorFlow Lite

> Documento de diseño técnico. Fase posterior al piloto (el MVP usa la
> heurística HSV de `mobile/lib/core/vision/dpd_analyzer.dart`).
> Proyecto **Yakuni** — Hackathon Kuska Wiñasun UNH 2026.

## 1. Objetivo

Elevar la exactitud de la estimación del cloro residual libre por cámara,
reemplazando la heurística de color HSV (Fase 1/MVP) por un **modelo de
aprendizaje automático entrenado con fotografías reales del piloto**, que
ejecuta **on-device y sin internet** (TensorFlow Lite) en teléfonos de gama baja.

**Meta de exactitud:** ≥ 90 % de acierto de *rango de riesgo* (verde/amarillo/rojo)
y error absoluto medio ≤ 0.15 mg/L en el rango 0–1.0 mg/L. Referencia científica:
González-Gómez et al. (2025) alcanzan > 84 % clasificando cloro libre con cámara
de smartphone y corrección de color.

### Por qué se difiere a después del piloto
El modelo necesita **cientos de fotos reales** bajo iluminación de campo (sol,
sombra, interior). Ese dataset **solo existe tras el piloto**, y el propio MVP lo
recolecta (ver §2). Mientras tanto, la heurística HSV + confirmación manual es
demostrable y honesta.

---

## 2. Recolección de datos (el MVP ya la hace)

La clave del diseño: **HU-05 (lectura por cámara con confirmación) + HU-08
(evidencia fotográfica)** ya producen pares etiquetados sin trabajo extra.

Cada lectura genera un ejemplo de entrenamiento:

```
  ENTRADA                                          ETIQUETA (ground truth)
  ───────                                          ───────────────────────
  foto del comparador DPD + tarjeta de calibración   →   cloro confirmado/corregido
                                                         por el operador (mg/L)
```

### Esquema del dataset
Se aprovecha la evidencia ya subida (`evidencia_foto`) más el valor y método de
la medición (`medicion.cloro_mg_l`, `medicion.metodo_cloro = 'CAMARA_DPD'`).

| Campo | Origen | Uso |
|-------|--------|-----|
| `ruta_archivo` (imagen) | `evidencia_foto` | Entrada X |
| `cloro_mg_l` (confirmado) | `medicion` | Etiqueta y |
| `nivel_riesgo` | `medicion` | Etiqueta de clasificación |
| `metodo_cloro` | `medicion` | Filtro (solo `CAMARA_DPD`) |
| `fecha_hora`, `latitud/longitud` | `medicion`/`evidencia` | Estratificar por hora/luz/lugar |

> **Endpoint de exportación sugerido (Fase 2):** `GET /ml/dataset` (rol DESA/ADMIN)
> que devuelve el índice `imagen → cloro` del piloto para entrenar fuera de línea.

### Buenas prácticas de datos
- **Balancear clases**: en campo abundan las lecturas verdes; sobremuestrear
  amarillo/rojo o usar *class weights*.
- **Estratificar por condición de luz** usando `fecha_hora` (mañana/tarde) para
  cubrir sol/sombra.
- **Curación**: descartar fotos borrosas o sin tarjeta de calibración visible.
- **Privacidad (Ley N.° 29733)**: las imágenes son de muestras de agua, no de
  personas; aun así, anonimizar metadatos y almacenar con acceso restringido.

---

## 3. Preprocesamiento

Reutiliza y extiende lo que ya hace `dpd_analyzer.dart` (recorte central y
corrección por tarjeta de calibración):

```
1. Detección de la tarjeta de calibración (parches de color de referencia)
2. Corrección de color / balance de blancos  (color constancy)
      → normaliza la iluminación: la misma muestra se ve igual bajo sol o sombra
3. Recorte de la región de la muestra (tubo DPD)
4. Redimensionar a la entrada del modelo (p. ej. 64×64 ó 96×96)
5. Normalización de píxeles a [0,1] ó [-1,1]
```

La corrección con la tarjeta es lo que hace **transferible** el modelo entre
teléfonos y luces distintas — sin ella, el color crudo no es comparable.

---

## 4. Modelo

Dos formulaciones (se pueden entrenar ambas y elegir por métrica):

| Formulación | Salida | Ventaja |
|-------------|--------|---------|
| **Regresión** | cloro en mg/L (continuo) | Da el número que el operador confirma; reutiliza el motor de reglas para el semáforo |
| **Clasificación** | verde/amarillo/rojo (3 clases) | Más robusta con pocos datos; alineada al Desafío 2 |

**Arquitectura recomendada (MVP de la Fase 2):** red convolucional **diminuta**
(2–3 bloques Conv+ReLU+Pool → GAP → densa), o **MobileNetV3-Small** con
*transfer learning* si hay pocos datos. Objetivo de tamaño: **< 500 KB**
cuantizado, para gama baja.

> Alternativa sin CNN: como la señal es esencialmente **color**, un modelo
> clásico (regresión/gradient boosting sobre features HSV/Lab del parche
> calibrado) puede rivalizar con la CNN y es aún más ligero. Conviene compararlo
> como *baseline* fuerte frente a la heurística actual.

---

## 5. Entrenamiento

- **Framework:** TensorFlow/Keras (PC o Colab; no en el teléfono).
- **Split:** 70/15/15 (train/val/test) **estratificado por nivel** y separado por
  reservorio para evitar fuga de datos.
- **Aumentos:** brillo, contraste, rotación leve, ruido — simulan variación de
  campo.
- **Métricas:**
  - Clasificación: *accuracy* de rango, matriz de confusión, **recall del rojo**
    (falsos negativos de agua no segura = lo más costoso).
  - Regresión: MAE y RMSE por tramo de concentración.
- **Criterio de promoción a producción:** superar a la heurística HSV actual en
  el set de test **y** recall de rojo ≥ 0.95.

---

## 6. Conversión a TensorFlow Lite

```python
converter = tf.lite.TFLiteConverter.from_keras_model(modelo)
converter.optimizations = [tf.lite.Optimize.DEFAULT]      # cuantización
converter.representative_dataset = generador_representativo # int8
tflite_model = converter.convert()
open('dpd_model.tflite', 'wb').write(tflite_model)
```

- **Cuantización int8**: reduce tamaño ~4× y acelera en CPU de gama baja.
- Verificar que la exactitud tras cuantizar no cae > 1–2 puntos.

---

## 7. Integración en la app (cambio *drop-in*)

La interfaz de estimación **no cambia**: hoy `estimarCloro(r,g,b)` en
`dpd_analyzer.dart`; en Fase 2 se añade un estimador por modelo con la **misma
firma de salida** (`DpdResultado`), de modo que la pantalla de cámara, la guía de
encuadre, la **confirmación manual** y el semáforo se quedan igual.

```dart
// pubspec.yaml (Fase 2)
//   tflite_flutter: ^0.11.0
//   assets: [ assets/models/dpd_model.tflite ]

class DpdModeloTflite {
  late final Interpreter _interprete;

  Future<void> cargar() async {
    _interprete = await Interpreter.fromAsset('assets/models/dpd_model.tflite');
  }

  DpdResultado estimar(img.Image muestraCalibrada) {
    final entrada = _preprocesar(muestraCalibrada);   // recorte + normalización
    final salida = List.filled(1, 0.0).reshape([1, 1]);
    _interprete.run(entrada, salida);
    final cloro = salida[0][0].clamp(0.0, cloroMaxDpd);
    return DpdResultado(
      cloroEstimado: cloro,
      confianza: /* de la salida del modelo */ 0.9,
      nivelEstimado: clasificar(cloroMgL: cloro).nivel,
      hue: 0, saturation: 0, value: 0,
    );
  }
}
```

**Estrategia de despliegue segura:**
1. El modelo corre **junto** a la heurística HSV; si el modelo no está seguro
   (baja confianza) o el asset no cargó, **cae en HSV** (degradación elegante).
2. Se mantiene **siempre** la confirmación/corrección del operador (transparencia
   del algoritmo — requisito del documento de diseño).
3. *Feature flag* para activar el modelo por versión/piloto.

---

## 8. Bucle de mejora continua (MLOps ligero)

```
   piloto ──▶ nuevas fotos + confirmaciones ──▶ dataset crece
      ▲                                              │
      │                                     reentrenar + evaluar
      │                                              │
   app usa modelo  ◀── publicar dpd_model.tflite ◀──┘ (si supera al anterior)
```

- **Versionar** el `.tflite` (v1, v2…) y registrar su exactitud.
- **Telemetría de correcciones**: cuánto corrige el operador el valor del modelo
  es la señal directa de calidad en producción.

---

## 9. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|-----------|
| Pocos datos del piloto | Empezar con clasificación + transfer learning + aumentos; baseline clásico |
| Variabilidad de iluminación | Tarjeta de calibración obligatoria + corrección de color |
| Falsos negativos de rojo (grave) | Optimizar recall del rojo; umbral conservador; el operador confirma |
| Peso/latencia en gama baja | Modelo < 500 KB, int8, entrada pequeña; fallback a HSV |
| Sesgo por reservorio/turno | Split por reservorio; estratificar por hora |

---

## 10. Criterios de aceptación (Fase 2)

- **CA-F2-01**: dado el set de test del piloto, el modelo clasifica el rango de
  riesgo correcto en ≥ 90 % de los casos.
- **CA-F2-02**: el *recall* del nivel rojo es ≥ 0.95 (no dejar pasar agua no
  segura).
- **CA-F2-03**: la inferencia corre en < 1 s en un Android 8 / 2 GB RAM, sin
  conexión.
- **CA-F2-04**: si el modelo falla o no está seguro, la app usa la heurística HSV
  sin interrumpir el registro.
- **CA-F2-05**: el valor estimado por el modelo **siempre** admite confirmación o
  corrección manual antes de guardar.

---

## 11. Roadmap

| Hito | Entregable | Depende de |
|------|-----------|-----------|
| F2.0 | Endpoint `GET /ml/dataset` y exportación del piloto | Evidencia subida (HU-08 ✅) |
| F2.1 | Baseline clásico (features de color) vs HSV | Dataset F2.0 |
| F2.2 | CNN diminuta / MobileNetV3-Small entrenada | Dataset F2.0 |
| F2.3 | `dpd_model.tflite` cuantizado + evaluación | F2.1/F2.2 |
| F2.4 | Integración `DpdModeloTflite` con fallback + feature flag | F2.3 |
| F2.5 | Bucle de reentrenamiento y telemetría de correcciones | F2.4 |

---

## Referencias
- González-Gómez, M. et al. (2025). *Color QR codes for smartphone-based analysis
  of free chlorine in drinking water.* Sensors, 25(11), 3251.
- MINSA (2011). *Reglamento de la calidad del agua para consumo humano
  (D.S. N.° 031-2010-SA).*
- Documentos del proyecto: `Yakuni_Analisis.docx`, `Yakuni_Diseno_Proyecto.docx`,
  `Yakuni_Herramientas_Tecnologicas.docx`.

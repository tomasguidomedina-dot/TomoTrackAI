# TomoTrackAI v0.2.1 — Ventana única de seguimiento

## Confirmado en la Mac del usuario (AE 2024 / Intel / macOS Monterey)
- Native Check v0.0.3: carga y dibuja señal visual.
- ROI Select v0.1.0: arrastre del recuadro sobre el visor de composición.
- **TomoTrackAI v0.2.0**: el usuario confirmó seguimiento NanoTrack perfecto sobre un video real y creación de un Null.
- Primer fallo intermitente detectado: «Motor NanoTrack no iniciado» al abrir el panel; reintentó y funcionó. Origen encontrado en `bridge/extension/panel.js`: `rpc` rechazaba comandos si llegaban antes del saludo de inicio del proceso Python congelado.

## Objetivos v0.2.1
**Una sola ventana operativa:** abrí Ventana > Extensiones (heredadas) > **TomoTrackAI** y seleccioná una capa de video. «Preparar objetivo» instala/activa automáticamente el efecto nativo ROI Select en la capa y permite arrastrar el punto en el visor de composición. El tamaño del ROI y su visibilidad se controlan en el mismo panel. «Analizar», «Corregir» y «Crear Null» también se controlan ahí.

El motor NanoTrack V2 es un ejecutable local e independiente por seguridad/rendimiento; el overlay y el punto arrastrable usan el efecto nativo de AE. **Son dos componentes técnicos, pero no deberían requerir dos operaciones manuales ni dos ventanas**. No afirmar que el seguimiento ocurre dentro del binario `.plugin`; sucede en el motor empaquetado.

### Corrección del arranque
`launch()` espera la respuesta inicial `{"ok":true,"ready":true}`, mantiene desactivados los botones de análisis hasta ese momento y ofrece «Reintentar motor». `rpc()` espera a `launch()` en vez de rechazar por una carrera de inicialización.

## Verificación
Compilar y empaquetar en GitHub Actions no demuestra que el flujo unificado funcione en AE 2024; queda pendiente probarlo en la máquina real. La versión 0.2.0 que sí siguió y creó el Null sigue preservada en `stable/tracking-v0.2.0`.

El instalador v0.2.1 actualiza el panel CEP y el motor; **preserva** el efecto nativo ROI Select que ya funciona, además de las versiones anteriores.

## Límites conocidos
Solo metraje de video local, sin precomposiciones, sin remapeo temporal ni cambio de velocidad; AE 2024 Mac Intel. Requiere acceso a Internet durante la instalación inicial de los modelos ONNX, cuyos SHA se verifican. No se necesita Python/Xcode instalados por el usuario.

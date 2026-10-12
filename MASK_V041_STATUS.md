# TomoTrackAI v0.4.1 — CANDIDATO EXPERIMENTAL, no estable

## Base comprobada y objetivo
El usuario confirmó en su MacBook Intel 2015 (Monterey, AE 2024) que **v0.3.2** inicia NanoTrack en **1,6 segundos**, sigue 36 fotogramas correctamente en menos de un minuto y genera el Null. En **v0.4** observó espera cercana a 60 segundos y una rotación que tiembla incluso cuando el objeto no gira.

Esta rama parte expresamente de `stable/mask-tracking-v0.3.2-tested`, no del motor v0.4 defectuoso. Conserva la estructura de inicio de NanoTrack y aísla la estimación nueva en `engine/rotation_estimator.py`. Su importación y ejecución se producen después de que el motor inicializó y solamente si el usuario habilitó Rotación. Las mediciones de GitHub CI no representan una garantía de arranque en Monterey 2015.

## Qué integra, en un solo panel
- Máscara nativa en modo None: conserva el video intacto, sigue usando caja envolvente para NanoTrack.
- Posición X/Y por NanoTrack V2.
- Escala X/Y según dimensiones del objeto detectado (variaciones de caja pueden introducir ruido; todavía no hay Perspective Corner Pin).
- Rotación 2D opcional, desacoplada de NanoTrack: puntos KLT restringidos a ROI, chequeo ida/vuelta, filtrado de outliers con RANSAC, soporte espacial amplio, inliers mínimos, comparación respecto de un ancla y no sumatoria ingenua de pequeños giros, banda muerta de 1.25 grados, confirmación temporal. Si no hay evidencia suficiente, **congela el ángulo** e indica el motivo.
- Null con keyframes de Position, Scale y Rotation.
- Modos Supervisar (lotes de 1 cuadro + 350 ms de pausa), Equilibrado (2 cuadros + 160 ms) y Rápido (4 cuadros + 55 ms). Es **tiempo concedido al visor**, no confirmación de renderización física de AE.
- Pausa entre lotes y ajuste de máscara en línea de tiempo, continuando mediante reseed.
- Indicador de confianza NanoTrack, estabilidad angular y, cuando no es fiable, motivo de rechazo.

## Verificación rigurosa
`engine/tests_rotation.py` cubre seis situaciones que faltaban en v0.4: sujeto inmóvil, traslación, cambio de tamaño sin rotación, vibración subgrado, giro real y oclusión. La CI también ejecuta video real con ONNX NanoTrack y pruebas de ExtendScript de máscara y Null.

## Instalación segura, SIN Internet
`Instalar_TomoTrackAI.command` exige los mismos modelos ONNX que ya están instalados. **No los descarga**. Copia el motor nuevo a una carpeta temporal, ejecuta una prueba de inicio local de 18 segundos y **no sustituye el motor/panel existentes si no responde**. Solo después de superar esa verificación archiva y sustituye la instalación, sin tocar otros plugins. Guarda backups en `~/Library/Application Support/TomoTrackAI3/respaldos/`.

Los proyectos con el antiguo efecto independiente ROI Select no se reparan automáticamente. La herramienta sigue siendo una sola extensión CEP en Ventana > Extensiones heredadas > TomoTrackAI.

## Límites y precauciones
- **No declarar esta candidata estable** hasta que el usuario confirme en AE: inicio rápido, giro real correcto y ausencia de temblores en una toma sin giro, escala razonable, pausa/corrección y Null íntegro.
- El sistema de rotación está pensado para texturas suficientes. Con sujetos uniformes o muy borrosos, conservará el ángulo; esto es intencionado y preferible a inventar giros.
- El procesamiento sigue siendo 100 % local. No se han agregado llamadas de red en el motor.
- Sin rotación 3D, tracking de cuatro esquinas, remapeo de tiempo o precomposiciones.
- La base **v0.3.2 estable permanece sin modificaciones** en GitHub.

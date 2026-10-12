# TomoTrackAI v0.4 — Posición + Escala + Rotación y visor supervisable

## Qué contiene
- **Una sola entrada de TomoTrackAI** en Ventana > Extensiones (heredadas) de After Effects 2024, Mac Intel macOS Monterey.
- Selección con máscara libre nativa de AE (Pluma, tecla G), en modo Ninguno para no recortar el video.
- Posición X/Y: NanoTrack V2, mismo método principal de v0.3.2 que el usuario validó en metraje real.
- Escala X/Y: evolución del ancho y alto detectados por NanoTrack. No implica reconstrucción 3D.
- Rotación 2D: estimación complementaria OpenCV de esquinas ópticas KLT y transformación robusta RANSAC; se buscan puntos *dentro de la máscara dibujada* al iniciar el rastreo.
- Si el estimador no tiene suficientes puntos fiables, conserva el ángulo anterior y muestra la situación en el panel. No inventa una rotación.
- Máscara animada con traslado, escala y giro; corrección manual mediante Pausar, editar trazado, Aplicar corrección, Continuar.
- Null nativo exportado con keyframes Position, Scale X/Y (%) y Rotation (grados). Se puede desactivar Escala y Rotación en la interfaz antes de iniciar una sesión.
- Tres modos de avance visual: Supervisar (1 cuadro y 210 ms para dar margen al visor), Equilibrado (2 cuadros y 110 ms) y Rápido (4 cuadros y 35 ms). **El tiempo de espera permite el render, pero no garantiza que la GPU de AE haya terminado de pintar cada imagen**. Dejar el visor en resolución baja si es necesario.
- Indicadores de confianza NanoTrack y confiabilidad de la estimación del giro.
- Un instalador Mac Intel que respalda y sustituye el motor anterior y el panel v0.3.2, conservando los modelos y los archivos de respaldo.

## Cómo probar
1. Cerrar AE con Cmd+Q y ejecutar el instalador del ZIP. Modelos NanoTrack ya instalados se reutilizan; no requiere Internet si ya existen.
2. Abrir un proyecto de prueba, seleccionar un metraje simple, dibujar máscara cerrada alrededor del objeto.
3. Elegir en el panel Escala y Rotación; seleccionar modo **Supervisar**. Pulsar Iniciar.
4. Ver movimiento de máscara cuadro a cuadro. Probar Pausar, corregir el contorno y Continuar. Crear Null.
5. Revisar en el Null los keyframes Position, Scale y Rotation. Verificar que la capa de video sigue sin transformarse.
6. Probar también movimiento con escala significativa y giro visible. Si no hay textura suficiente, se puede mostrar «Giro: ángulo mantenido».

## Alcances y limitaciones
- NanoTrack V2 sigue una caja envolvente inicial, aunque la selección sea una máscara libre; el contorno de máscara se transforma con el track, pero **no hace segmentación píxel a píxel**.
- La rotación es estimada mediante puntos visuales y puede degradarse por desenfoque, oclusiones o superficies uniformes; su fiabilidad requiere pruebas en escenas reales de la Mac del usuario.
- El modo Supervisar puede reducir la velocidad total a cambio de dar tiempo al render asíncrono de AE. No podemos forzar que la imagen se dibuje instantáneamente.
- No admite precomposiciones, clips con time remapping, cambios de velocidad ni perspectiva (4-corner pin). No es un rastreador de superficies 3D.
- Los valores X/Y de Scale provienen de la caja rectangular; no hay escala física independiente de perspectiva.
- La rama `stable/mask-tracking-v0.3.2-tested` preserva el funcionamiento anterior validado. La v0.4 necesita prueba en AE 2024 del usuario antes de declararse estable.

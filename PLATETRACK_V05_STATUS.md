# TomoTrackAI v0.5.0 — candidato experimental PlateTrack

## Objetivo
Un único motor de seguimiento CPU basado en el núcleo de código abierto PlateTrack/OpenCV: posición, escala uniforme y rotación coherentes, derivados de una única matriz de similitud 2D por fotograma. Selección por máscara cerrada dibujada con la herramienta Pluma de AE 2024. Crea máscara animada y Null Position+Scale+Rotation.

## Cambios principales
- Elimina NanoTrack del motor v0.5. **No usa modelos ONNX y no realiza solicitudes de red.**
- Importa el núcleo original PlateTrack: detección de características, LK piramidal, RANSAC y refinamiento ECC. Se procesa en streaming, no se cargan secuencias Full HD enteras en RAM.
- La matriz origen->actual controla tanto forma de máscara como la posición, escala y rotación del Null. No se estima Scale comparando cajas rectangulares AABB.
- Los fotogramas inciertos reducen la confianza. Tras cinco pasos sin solución se detiene el análisis para corrección manual. La corrección redibuja la máscara y reinicia las referencias en ese fotograma.
- Panel nativo CEP de AE 2024, con ritmos Supervisar/Equilibrado/Rápido y diagnóstico de puntos/ECC.
- Mantiene sin alterar la instalación original de los motores TomoTrackAI3 y los ONNX de NanoTrack. Nueva carpeta de motor `TomoTrackAI5`.
- Instalador offline verifica el arranque real del nuevo binario con límite de 20s antes de modificar la instalación de paneles, archivando los paneles anteriores.

## Probar con un proyecto duplicado
1. Cerrar AE 2024 y ejecutar `Instalar_TomoTrackAI.command` (Intel Monterey).
2. Abrir AE > Ventana > Extensiones heredadas > TomoTrackAI.
3. Seleccionar una sola capa 2D de metraje original sin remapeo ni cambio de velocidad.
4. Dibujar una máscara cerrada sobre un objeto texturado y activar PlateTrack.
5. Probar giro sin cambio de tamaño: la escala del Null debe mantenerse cerca del 100%, mientras Rotation refleja el movimiento.
6. Probar zoom sin giro: Rotation debe permanecer estable.
7. Probar Pausar -> ajustar máscara -> Aplicar corrección -> Continuar, y generar Null.

## Limitaciones y seguridad
Esta es una candidata de prueba, **no certificada** contra el tracker nativo de Adobe ni validada aún en tu Mac. La homografía/perspectiva completa no está activada en la UI inicial; el modo predeterminado es similitud 2D, adecuado para posición, escala y rotación. El seguimiento de puntos puede degradarse por falta de textura, oclusiones y cortes de video. ECC puede fallar en cambios grandes; en ese caso no sustituye la estimación de LK.

El sistema no hace segmentación de personas ni deforma la silueta, solo transporta geométricamente la máscara. Para rotoscopia de extremidades o ropa se necesita una solución diferente.

La rama estable `stable/mask-tracking-v0.3.2-tested` sigue sin tocarse. No declarar la nueva versión estable hasta confirmar en macOS Monterey / Intel 2015 el arranque, precisión geométrica, memoria, pausa, corrección y Null.

# TomoTrackAI v0.6.2 — Correcciones manuales de cámara (candidata)

La v0.6.2 integra **pins de cuatro esquinas inspirados en el tracker original PlateTrack**, con residuo de corrección repartido sobre los diez cuadros previos, continuando el mismo motor local OpenCV streaming después de una pérdida de confianza. No incorpora reconocimiento automático multiescala ni un segundo tracker.

**Primera limitación fundamental:** al corregir tenés que reubicar *exactamente las cuatro esquinas del mismo parche físico del fondo*, en el mismo orden que al crear la máscara. No selecciones una región distinta, porque la matriz de cámara única no puede deducir cómo se relacionan dos regiones sin referencias comunes. Los cuatro puntos deben formar un cuadrilátero convexo. Si el área original sale de plano definitivamente, la reidentificación **no está resuelta**.

## Instalación sin romper versiones estables
Esta candidata se instala en paralelo: motor en \`~/Library/Application Support/TomoTrackAI62\` y extensión \`com.tomo.trackai62\`. **NO modifica** v0.5, v0.6 ni parche v0.6.1, que siguen siendo las versiones de referencia. Salí de After Effects antes de ejecutar \`Instalar_TomoTrackAI.command\` desde el ZIP completamente extraído.

En After Effects 2024: Ventana → Extensiones (heredadas) → **TomoTrackAI · Pins v0.6.2**.

1. Abrí una copia del proyecto. Seleccioná una capa de metraje original 2D sin transformación animada.
2. Elegí **Estabilización** y dibujá una máscara **cerrada con 4 vértices** sobre una región **estática con textura**. Ordená los vértices en sentido horario, empezando por esquina superior izquierda.
3. Pulsá **Analizar cámara**.
4. Si PlateTrack se detiene por baja confianza, el cabezal AE salta al fotograma de pérdida y se selecciona la máscara. **Mové los cuatro vértices existentes**, sin cambiar su orden, de modo que describan el **mismo fondo físico** (no otra pared/objeto).
5. Pulsá **Fijar 4 puntos del fondo**. El motor valida forma, correspondencia geométrica y disponibilidad de características para continuar. No hace falta repetir los fotogramas previos.
6. Pulsá **Continuar análisis**. Podés repetir el proceso si se vuelve a perder el fondo.
7. Terminada la secuencia, elegí **Movimiento suave** o **Cámara fija**, intensidad, radio de suavizado y recorte automático; luego **Crear capa estabilizada**.

Cuando el tracker realmente perdió muestras, permite interpolar solo un hueco de **hasta 8 fotogramas** tras fijar un pin. Estos cuadros se etiquetan como \`manual_interpolated=true\` con **confianza 0**. Su transformación se aproxima manualmente; **no es seguimiento real ni garantía de coincidencia con la cámara**. Revisalos en After Effects. PlateTrack original reparte el residuo de pin en diez cuadros precedentes; esta implementación realiza el mismo principio sobre matrices de similitud manteniendo un único sistema de referencia. La matriz nueva del tracker local se compone con la transformación fijada por el pin original, para que no se reinicie Position/Scale/Rotation en cada corrección.

Si la máscara no tiene cuatro puntos correspondientes, el zoom supera límites admisibles, el error entre esquinas no se explica con una similitud 2D, o la diferencia supera ocho cuadros sin detección, el motor muestra el motivo y **no construye una estabilización falsa**. En ese caso probá otra toma con más textura, reducís el tramo o esperá una versión con búsqueda/reidentificación automática.

## Pruebas incluidas
- Forma convexa y cuatro vértices ordenados; rechazo de máscara errónea.
- Solución exacta de una similitud 2D con posición/giro/zoom variable.
- Rechazo de correcciones con deformaciones fuera de la hipótesis 2D.
- Suavizado de correcciones sobre diez cuadros previos.
- Huecos de hasta ocho cuadros interpolados con confianza cero y etiquetas inequívocas.
- Rechazo de huecos mayores de ocho cuadros; pérdida sin pin sigue bloqueando estabilización.
- Sesión con dos anclas y huecos aceptados puede estabilizar sin invalidar la confianza de todo el clip.
- Recuperación de tracking real sobre video AVI/MJPG codificado, desde pérdida simulada en cuadro 20 hasta cuadro 33, manteniendo matriz global y proyectando vértices.
- Regresiones de PlateTrack v0.5 y estabilización v0.6.1.
- Binario Intel x86_64 empaquetado y arranque probado en runner GitHub Actions.

**Estado:** candidata experimental. Las pruebas de CI en Mac Intel no validan las interacciones gráficas concretas ni el rendimiento en el equipo 2015 macOS Monterey del usuario. No afirmar equivalencia con Warp Stabilizer ni recuperación automática de escenas sin textura.

# TomoTrackAI v0.6 — Estabilización de cámara (CANDIDATA)

## Qué hace
Mantiene el **seguimiento original PlateTrack** y suma un modo Cámara (misma biblioteca OpenCV / PlateTrack, sin motor de IA adicional). A partir de las matrices de seguimiento de una **región fija del fondo**, genera una transformación por fotograma para estabilizar sin renderizar un archivo nuevo: duplica la capa de video y escribe Position, Scale y Rotation en After Effects.

Matemática: PlateTrack produce W_i (referencia→fotograma). Cámara fija usa C_i = inv(W_i). Movimiento suave reconstruye la trayectoria S_i mediante regresión local lineal ponderada y aplica C_i = S_i @ inv(W_i). De esta forma un paneo lineal no queda artificialmente frenado. El recorte automático busca el zoom global mínimo que cubra los bordes para todos los fotogramas comprobando las cuatro esquinas con la matriz inversa; si necesitaría un zoom superior a 250% o no es factible se detiene con error, nunca oculta el problema.

El proyecto original PlateTrack incluye en \`platetrack/stabilize.py\` el render con \`warpPerspective\`; aquí el compositing lo hace After Effects con los keyframes geométricamente equivalentes. La prueba de equivalencia con el código original se ejecuta en CI.

## Instalación
Esta versión se instala **EN PARALELO** a tu v0.5: usa \`~/Library/Application Support/TomoTrackAI6\` y \`com.tomo.trackai60\`, sin sustituir el motor ni panel v0.5.

1. Duplicar el proyecto de After Effects antes de probar la candidata.
2. Salir completamente de AE.
3. Descomprimir el ZIP **completo** en una misma carpeta; doble clic en \`Instalar_TomoTrackAI.command\`.
4. AE 2024 > Ventana > Extensiones (heredadas) > \`TomoTrackAI · Estabilización v0.6\`.
5. Seleccionar **Estabilización**, una capa de metraje original 2D no alterada, y dibujar con Pluma (G) una máscara cerrada en una región **ESTÁTICA y TEXTURADA** del fondo. Evitá personas en movimiento.
6. \`Analizar cámara\` hasta el último fotograma.
7. Elegir \`Movimiento suave\` o \`Cámara fija\`, intensidad, suavizado y recorte/zoom automático; pulsar \`Crear capa estabilizada\`.
8. AE crea una copia sobre la capa original, conservando la original pero dejándola **desactivada**. El archivo fuente no se modifica. Deshacer en AE revierte la operación.

## Limitaciones iniciales (intencionales)
- Soporta metraje original con píxeles cuadrados y dimensiones iguales al video decodificado, capa 2D sin padre, sin remapeo, sin keyframes de Anchor/Position/Scale/Rotation/Opacity ni expresiones. Scale original 100%, Rotation 0°, Opacity 100%. Rechaza estos casos antes de duplicar.
- Estabilización 2D de similitud: compensación de traslación, giro y zoom uniformes. No incluye deformación tipo Warp Stabilizer, rolling shutter, paralaje ni perspectiva de múltiples planos.
- Requiere una región estática del fondo con textura suficiente; si se pierde el fondo, el motor reduce la confianza y la estabilización se rechaza en vez de inventar fotogramas. Para la v0.6 no se admiten correcciones de ancla intermedias durante estabilización: una sesión con varias anclas se rechaza para evitar cambios de sistema de coordenadas.
- \`Recorte automático\` puede aumentar el zoom; para movimientos extremos aborta si necesita más de 2.5×. Si se desactiva, pueden aparecer bordes negros. No rellena píxeles inexistentes.
- No se ha validado todavía en macOS Monterey sobre la Mac Intel 2015 del usuario. Validación automatizada en CI Mac Intel NO equivale a verificar AE real. No se puede afirmar que supera la precisión ni velocidad de Adobe Warp Stabilizer hasta comparar ambos con el mismo material.

## Pruebas incluidas
- Cámara quieta e identidad.
- Paneo uniforme: el modo suave conserva la traslación y los extremos de secuencia.
- Cámara fija compensa traslación, escala y rotación.
- Movimiento suave reduce la aceleración espuria conservando la tendencia de pan.
- Intensidad cero no modifica video.
- Zoom/recorte no produce píxeles negros en esquinas (verificado geométricamente).
- Corte por confianza insuficiente o por datos discontinuos.
- Rechazo de anclas corregidas y crop imposible.
- **Paridad exacta con \`platetrack/stabilize.py\`** mediante OpenCV al aplicar matrices.
- Video AVI codificado + seguimiento PlateTrack en streaming + datos para AE.
- Prueba ExtendScript simulada: crea duplicado y escribe 25 keyframes, no modifica transform original y rechaza fuente animada.
- Regresiones anteriores de máscara y Null de object tracking.

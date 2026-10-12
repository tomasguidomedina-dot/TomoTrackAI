# TomoTrackAI v0.3.1 — un solo plugin visible en After Effects

## Qué cambió respecto de las versiones anteriores

**No se instala ROI Select ni Native Check.** La única entrada de la herramienta será **Ventana > Extensiones (heredadas) > TomoTrackAI**. La selección se hace con la herramienta Pluma habitual de After Effects, dibujando una máscara poligonal cerrada sobre el objeto.

Para no recortar ni deformar la imagen original, TomoTrackAI pone la máscara en modo **Ninguno / None**, pero conserva su trazado visible y animable sobre la capa seleccionada. El motor NanoTrack V2 procesa el video fuente fuera del hilo de render. El panel escribe keyframes del trazado durante el procesamiento y adelanta el cabezal para mostrar su avance en el visor. Se puede pausar, editar los vértices de la máscara sobre ese fotograma, reiniciar el tracker en esa posición y continuar. El botón Crear Null exporta el movimiento a una capa nula sin alterar la capa original.

### Importante acerca de cómo funciona la máscara

En esta fase, la forma poligonal define la **región inicial de rastreo mediante su caja envolvente**, y se conserva la forma al trasladarla y escalarla con la trayectoria. **NanoTrack V2 no aplica todavía segmentación pixel a pixel para ignorar los píxeles fuera del polígono.** Es una limitación explícita de este motor. No equivale a rotoscopía ni a Object Matte.

## Instalación de una sola herramienta

1. Cerrar After Effects 2024.
2. Descomprimir el ZIP y ejecutar `Instalar_TomoTrackAI.command`.
3. El instalador copia el motor autónomo Intel, descarga modelos ONNX con verificación SHA y registra una única extensión.
4. Ofrece archivar y retirar **exclusivamente las entradas anteriores de TomoTrackAI**, y avisa que proyectos que usaban viejos efectos pueden mostrarlos como ausentes. Hace respaldo antes de borrar.
5. Abrir AE > Ventana > Extensiones (heredadas) > TomoTrackAI. En la línea de tiempo seleccionar **una sola capa de video archivo**.
6. Pulsar Pluma (G), dibujar y cerrar una máscara alrededor del objeto. Pulsar Iniciar.
7. Durante el análisis la máscara recibe nuevas claves y el visor avanza; para corregir, Pausar, editar la máscara en ese fotograma y Aplicar corrección.
8. Crear Null exporta las posiciones a keyframes.

**Para ver el contorno:** activar Ver > Mostrar controles de capa, mantener la capa seleccionada y seleccionar su máscara.

## Arranque del motor y rendimiento

El panel muestra cuánto tarda el motor en anunciarse listo, y arranca NanoTrack mientras se dibuja la máscara. Las acciones esperan a que esté listo. Esto evita el error de carrera «Motor NanoTrack no iniciado», aunque el tiempo de carga real dependerá del hardware y de macOS. GitHub Actions mide el arranque del ejecutable en macOS Intel y muestra su resultado en los registros; esa medición no representa automáticamente el rendimiento en un MacBook Pro 2015 con 8 GB.

La CPU se limita a dos hilos OpenCV como en la versión probada. La integración evita renderizado externo manual. Se reutiliza el núcleo del tracking v0.2 cuya precisión y exportación de Null fueron confirmadas por el usuario.

## Validación pendiente

La compilación del ZIP, las pruebas con video real de NanoTrack y la verificación de sintaxis no demuestran por sí solas que la máscara se dibuje, se anime y pueda corregirse dentro de AE 2024. **No considerar esta versión estable sin esa prueba en la Mac del usuario.**

## Limitaciones por ahora

Solo clips de video locales (no precomposiciones), capas 2D sin remapeo de tiempo ni estiramiento; no soporte de perspectiva o rotación autónoma ni segmentación exacta de máscara. La máscara animada puede mostrar la selección en el visor de composición, pero depende de tener visibles los controles de capa. El panel también muestra avance numérico.

### Copias estables conservadas en GitHub

- `stable/native-render-v0.0.3`
- `stable/native-roi-select-v0.1.0`
- `stable/tracking-v0.2.0` — seguimiento real y Null confirmados

La rama de v0.3 es experimental y no se fusiona hasta validar funcionamiento en After Effects.

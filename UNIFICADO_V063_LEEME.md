# TomoTrackAI v0.6.3 — UNIFICADO, con controles nativos de 4 puntos

## Ya NO hay tres paneles
Una sola extensión llamada **TomoTrackAI** en
**After Effects 2024 → Ventana → Extensiones (heredadas) → TomoTrackAI**.
Dentro tiene Seguimiento de objetos, Estabilización y Corrección de cámara.

El instalador de esta versión usa \`com.tomo.trackai\` y el motor canónico
\`~/Library/Application Support/TomoTrackAI/engine/TomoPlateTrack/\`.
**Archiva** los paneles CEP antiguos identificados como TomoTrackAI
(\`com.tomo.trackai50\`, \`com.tomo.trackai60\`, \`com.tomo.trackai62\`, etc.)
dentro de \`~/Library/Application Support/TomoTrackAI/respaldos-extensiones/\`
sin eliminarlos. Los motores antiguos y los proyectos .aep no se borran.
Un script de rollback está incluido. Si tenías una extensión instalada para
*todos* los usuarios bajo \`/Library/Application Support/Adobe/CEP/extensions\`,
el instalador solo informa: no la elimina sin permiso de administrador.

## Instalación
1. **Salir de After Effects totalmente con Cmd+Q.**
2. **Descomprimir todo el ZIP** en una carpeta. NO ejecutar el .command desde
   la vista previa del ZIP.
3. Abrir \`Instalar_TomoTrackAI_Unificado.command\`.
4. El instalador primero prueba que arranque el motor Intel. Luego respalda
   y oculta del menú los paneles antiguos. Si el proceso falla, intenta revertirlo.
5. Abrir AE 2024. Debe aparecer solo **TomoTrackAI**.
6. Probalo sobre una **copia** del proyecto, no sobre un trabajo en producción.

## Recuperar una estabilización tras pérdida de confianza
1. Elegí **Estabilización**, seleccioná un video 2D (archivo original, no precomp),
   dibujá una **máscara cerrada de EXACTAMENTE cuatro vértices** sobre una
   región fija del fondo que tenga detalles visibles. Los puntos deben rodear
   la misma región física durante la corrección (no un fondo nuevo).
2. **Analizar cámara**. Si baja a 0% y PlateTrack se detiene, el panel muestra
   automáticamente el cuadro de pérdida y agrega **cuatro efectos nativos
   «Punto de control»** sobre la capa, llamados:
   * TomoTrackAI • 1 Superior izq.
   * TomoTrackAI • 2 Superior der.
   * TomoTrackAI • 3 Inferior der.
   * TomoTrackAI • 4 Inferior izq.
3. Si no aparece el visor con cruces, abrí **Controles de efectos** de esa
   capa; seleccioná un «Punto de control». Sus puntos son editables en el
   visor de composición de Adobe cuando los controles de capa están visibles.
   Podés editar sus coordenadas numéricas en Controles de efectos si no ves
   la cruz. El botón **Mostrar 4 puntos** vuelve a enfocarlos sin borrar tus
   posiciones ya corregidas.
4. Mové las cuatro cruces a las **MISMAS cuatro esquinas** de esa región
   (manteniendo orden). **Aplicar corrección de 4 puntos** ahora *lee esos
   valores*, NO la máscara original, y rechaza pulsaciones si ninguno se movió.
5. **Continuar análisis**. Se suaviza el enlace y si hubo cuadros sin
   tracking se interpolan manualmente hasta 8 fotogramas, marcados como
   \`manual_interpolated\`, confianza 0. Revisá esos cuadros en AE.
6. Finalmente **Crear capa estabilizada**.

Si el área elegida desaparece del plano o sufre una transformación no
aproximable por posición/escala/rotación 2D, el motor **rechaza el pin** para
no inventar datos. No existe búsqueda global multiescala automática aún.
El plugin sigue siendo una alternativa geométrica 2D, no reemplazo universal
de Warp Stabilizer (rolling shutter, perspectiva, paralaje pronunciado).

## Seguridad / Rollback
El instalador no modifica el archivo de video ni proyectos .aep. El modo
Estabilización duplica la capa y desactiva la original; deshacer en AE revierte
la operación. Los cuatro efectos «Punto de control» se eliminan tras aplicar
correctamente la corrección.

Si una versión anterior era mejor, cerrá AE y ejecutá
\`Restaurar_Paneles_TomoTrackAI.command\` del ZIP; repondrá los paneles guardados.
Hasta que confirmemos visualmente la creación/manipulación de los cuatro puntos
en After Effects 2024 macOS Monterey Intel, esta versión es **candidata para
pruebas** y no debe sustituir trabajos críticos sin backup.

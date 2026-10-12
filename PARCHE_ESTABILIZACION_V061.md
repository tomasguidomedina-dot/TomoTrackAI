# TomoTrackAI v0.6.1 — Parche del botón Crear capa estabilizada

## Causa probable
En v0.6 el botón dependía de \`trackCompleted\`, una bandera de estado del navegador que solo se activaba cuando el **último** mensaje \`step\` traía a la vez \`ended=true\` y \`new.length>0\`. Algunas secuencias terminaban con lote vacío o en otro orden, y el panel mostraba botón deshabilitado.

## Solución
- Con una sesión de estabilización ya inicializada (\`hasData\`), el botón se habilita, sin depender de \`trackCompleted\`.
- El motor, **sin modificaciones**, autoriza la acción únicamente si alcanzó el final real del video. Si no, muestra un error específico. Se mantienen las validaciones del motor para confianza, continuidad, recorte geométrico, etc.
- La interfaz distingue fin auténtico del último frame \`last_frame\` vs un EOF prematuro y detecta el último lote incluso si tiene cero muestras nuevas.
- El botón no se habilita mientras el análisis sigue ocupado, sin datos ni tras aplicar una estabilización.
- No se cambian binario, motor, ecuaciones de estabilización, \`index.html\`, JSX, máscaras, versiones de plugin ni v0.5.

## Instalar
1. Salir de After Effects (**Cmd+Q**). Esto también cierra la sesión de tracking actual; habrá que repetir el análisis.
2. Descomprimir **todo** el ZIP.
3. Ejecutar \`Instalar_Parche_Estabilizacion_v061.command\` desde la carpeta extraída.
4. Abrir AE 2024 > Ventana > Extensiones (heredadas) > \`TomoTrackAI · Estabilización v0.6\`.
5. Seleccionar modo Estabilización, máscara sobre fondo estático, analizar y pulsar Crear capa estabilizada.
6. Si el motor detecta análisis incompleto o referencias perdidas, ahora responderá con un error explícito y el botón seguirá disponible para reintentar cuando corresponda.

Incluye \`Restaurar_Parche_Estabilizacion_v061.command\` por si necesitás recuperar el panel anterior.

**La v0.6 sigue siendo experimental hasta comprobar la exportación real en After Effects 2024 macOS Monterey.**

# TomoTrackAI — UI Adobe + identidad Tomo (v0.5.1)
Candidato de **cambio exclusivamente visual**, basado en la v0.5 de PlateTrack verificada en After Effects 2024 de Mac Intel Monterey. No se modifica el motor ni sus matrices, las pruebas de precisión ni las funciones del puente AE.

Secciones: Objetivo (capa/comp/máscara una vez que comienza la sesión), Seguimiento (Iniciar/Continuar, Pausar, Avanzar un fotograma, Corregir), Resultado (Crear Null, Nueva sesión), Actividad y Ajustes avanzados (único ajuste funcional: vista previa; modelo Similitud 2D y ECC se muestran como valores fijos). Estado del motor y confianza visibles sin tarjetas decorativas. Estética neutral Adobe 2024, acento azul reservado a la identidad y acción primaria.

## Instalación y reversión
1. Cerrá After Effects.
2. Extraé **todo** el ZIP del parche en una carpeta.
3. Ejecutá **Instalar_Interfaz_TomoTrackAI.command** desde esa carpeta (junto a panel.js e index.html). No necesita volver a descargar los ~90 MB del motor.
4. Abrí AE 2024 y verificá el panel. Tu motor PlateTrack v0.5 es el mismo.
5. Si preferís el panel anterior, cerrá AE y ejecutá **Restaurar_Interfaz_TomoTrackAI.command**.

El instalador verifica que existe la instalación PlateTrack y hace copia de los dos archivos visuales antes de reemplazarlos. No modifica el binario, sus modelos, los scripts JSX, los ajustes del tracking ni el manifest. No necesita Internet.

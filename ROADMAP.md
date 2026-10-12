# TomoTrackAI — progreso comprobado

## Native Check v0.0.3 — validado por el usuario

Configuración comprobada: AE 2024, macOS Monterey Intel. El usuario reportó que la capa se ve con **marco, recuadro, cruz y tinte verde**. Copia preservada en la rama `stable/native-render-v0.0.3`.

## ROI Select v0.1.0 — EN EXPERIMENTACIÓN

Rama `feature/native-target-selector` separada: este efecto debe aparecer en `Tomo FX > TomoTrack ROI Select`, con un parámetro **Punto objetivo** para ubicarlo mediante el control de punto nativo de AE, **Ancho region**, **Alto region** y **Mostrar region**. El marco se dibuja en el fotograma solo cuando el checkbox está activo. No debe teñir toda la imagen.

IMPORTANTE: compilar en CI NO demuestra que funcione en AE 2024. Requiere prueba en el equipo del usuario. No modifica la v0.0.3, ya validada.

## Funciones siguientes

1. Probar arrastre de punto en el visor de composición y respuesta de la ROI.
2. Integrar un motor temporal real de tracking NanoTrack/OpenCV, con frames y confiabilidad.
3. Corregir puntos perdidos; exportar movimiento a un Null de After Effects.
4. Optimizar rendimiento en Intel 8 GB RAM y empaquetado final.

No confundir el marcador ROI con un tracker que sigue objetos automáticamente.

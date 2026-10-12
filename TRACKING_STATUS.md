# TomoTrackAI v0.2 — Integración nativa + NanoTrack

## Qué está implementado (requiere validación del usuario en AE 2024)
- **Selector nativo ROI v0.1.0** (Rust AE Effect) previamente confirmado por el usuario.
- Motor OpenCV **NanoTrack V2** siguiendo cuadros reales del video fuente.
- Controles de analizar, un cuadro, detener, corregir la selección y crear Null.
- Keyframes de punto y tamaño en el **efecto nativo ROI**; el recuadro se desplaza en AE.
- Null con posición animada; sin cambio de escala; capa de video original sin deformación.
- Empaquetado del motor como ejecutable con PyInstaller para Intel; no Python manual.
- Modelos ONNX descargados por instalador **desde el repositorio del autor** con SHA1 verificado. Requiere conexión inicialmente.

## Arquitectura honesta
El seguimiento temporal corre en proceso local, no en PF_Cmd_RENDER. Una extensión CEP mínima conecta el proceso y el proyecto; no se presenta el panel como el efecto nativo. El recuadro/selector sigue siendo un verdadero archivo `.plugin`.

## Límites vigentes
Solo archivos de video 2D sin remapeo temporal, sin precomposiciones. Si AE tiene el clip modificado con time stretching o reelaboraciones complejas, esta build no admite la correspondencia de fotogramas. El rendimiento depende de tamaño/duración y Mac Intel 8 GB.

### No dar por probado hasta validar en la máquina destino
Que GitHub produzca un `.plugin` y un executable macOS **NO** demuestra que NanoTrack funcione en AE 2024. Hay que instalar y realizar seguimiento sobre un video real. Mantener v0.0.3 y v0.1.0 estables sin sobrescribirlas.

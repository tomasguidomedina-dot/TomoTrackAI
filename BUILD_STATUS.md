# Estado real del proyecto

- Este proyecto contiene un **efecto nativo de diagnóstico** y un flujo para compilarlo en GitHub Actions.
- El efecto dibuja un cuadro verde sobre la imagen y expone parámetros para desplazarlo.
- No incorpora seguimiento automático, correcciones temporales ni exportación a Null; esas funciones están pendientes.
- Un artefacto de GitHub Actions solo se publica si la compilación, la estructura del bundle, la arquitectura Intel, el plist y la firma ad-hoc pasan la comprobación automatizada.
- La compilación no demuestra compatibilidad real con After Effects 2024 ni con macOS Monterey. Requiere prueba en la computadora de destino.
- Se emplean las vinculaciones Rust `after-effects` 0.4.0 y `pipl` 0.1.1 basadas en la API C del SDK de After Effects. Esto produce un plugin nativo, **no** un panel CEP.
- El binario lleva identificador propio; no se reemplazan versiones anteriores.

**Nunca anunciar esta compilación como TomoTrackAI 2.0 funcional.** Solo es un paso para comprobar que el motor nativo carga correctamente.

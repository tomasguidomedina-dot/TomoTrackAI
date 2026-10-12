# TomoTrackAI 2.0

Proyecto de seguimiento de objetos para **After Effects 2024 / macOS Monterey / Intel x86_64**.

**Estado:** fase de validación de efecto nativo; todavía **NO** es un tracker completo.

## Lo que ya está en este repositorio

- `src/lib.rs`: efecto **nativo**, sin panel CEP, con cuadro de prueba sobre la imagen.
- `build.rs`: definición del efecto y recurso PiPL de After Effects.
- `.github/workflows/mac-intel.yml`: compilación automática con ejecutor macOS Intel.
- `scripts/Install_TomoTrack.command` y `scripts/Uninstall_TomoTrack.command`: instalador y desinstalador independientes.
- `BUILD_STATUS.md`: alcance y limitaciones verificables.

La implementación utiliza las bibliotecas abiertas **after-effects 0.4.0** y **pipl 0.1.1** (API nativa de After Effects mediante Rust), por lo que **no requiere distribuir el SDK propietario de Adobe**. Referencia: [Rust bindings](https://github.com/virtualritz/after-effects) y [Adobe C++ SDK Guide](https://ae-plugins.docsforadobe.dev/).

## Qué hace por ahora

El efecto `Tomo FX > TomoTrack Native Check` debe dibujar un recuadro verde, con controles de posición X/Y y tamaño. Sirve para validar carga nativa, procesado de píxeles y parámetros; **aún no realiza seguimiento automático**.

## Compilación y descarga

Abrí [Actions — TomoTrack Native macOS Intel](https://github.com/tomasguidomedina-dot/TomoTrackAI/actions/workflows/mac-intel.yml). Si aparece una ejecución **verde**, su sección *Artifacts* deberá ofrecer `TomoTrack_Native_Check_Mac_Intel` con un ZIP del bundle y los instaladores. El flujo sólo sube el artefacto cuando pasa la compilación y las verificaciones automatizadas.

**Si la ejecución falla o no hay artefacto, todavía no hay un instalador válido.** No se debe renombrar el código como si fuera un binario real. Compilar no certifica compatibilidad con AE 2024 ni macOS Monterey: hace falta prueba real en el Mac.

## Objetivo posterior

Seleccionar una región directamente en la imagen, seguirla en el tiempo con NanoTrack, permitir correcciones y exportar keyframes a un Null. No modificar ni desinstalar las versiones previas antes de disponer de una versión nueva comprobada.

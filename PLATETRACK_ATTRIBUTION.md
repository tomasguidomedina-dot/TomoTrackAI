# PlateTrack: atribución y reutilización

Motor original: [comfyui-platetrack](https://github.com/edgarciavfx/comfyui-platetrack), desarrollado por edgarciavfx y colaboradores.

Se incluyen los archivos `platetrack/{__init__.py,features.py,lk.py,models.py,refine.py,types.py,tracker.py}` obtenidos de la rama principal de ese proyecto en octubre de 2026. En `pyproject.toml` el autor declara una **licencia MIT**. No se encontró un archivo LICENSE en la raíz durante la consulta. Antes de redistribuir fuera de pruebas, verificar el texto completo de la licencia con el autor.

El adaptador `engine/platetrack_engine.py` implementa una interfaz de lectura progresiva, protocolo local JSONL y enlace After Effects a partir del núcleo de PlateTrack. **No se incluye ComfyUI, PyTorch, Cutie ni modelos descargables.**

Este paquete conserva crédito y enlaces al trabajo original y no implica patrocinio ni afiliación al autor de PlateTrack.

# AI Content Factory — MVP local con Ollama

Herramienta local para investigar un tema, preparar un guion factual para **Archivo Imposible** y generar un kit por escena para producir el video. Ollama redacta el guion y los prompts visuales; Gemini, Qwen y Clipchamp se usan manualmente siguiendo el kit.

## Requisitos

- Python 3.10 o posterior.
- Ollama instalado y abierto en la misma computadora donde vas a ejecutar este proyecto.
- Un modelo descargado en Ollama. El valor inicial es `qwen2.5:3b`.
- Internet para buscar referencias iniciales en Wikipedia.

## Preparación en Windows

Abrí PowerShell en la carpeta del proyecto:

```powershell
cd ai-content-factory
ollama pull qwen2.5:3b
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Si PowerShell bloquea la activación del entorno, podés ejecutar los comandos de Python usando `.venv\Scripts\python.exe`.

Comprobá que el servidor responda y que el modelo esté disponible:

```powershell
python generate.py --check-ollama
```

Si todavía no descargaste el modelo, ejecutá `ollama pull qwen2.5:3b` y volvé a comprobar.

## Generar un video

```powershell
python generate.py --account archivo_imposible --topic "El desastre del lago Nyos"
```

Ollama debe estar activo y tener descargado el modelo seleccionado. El programa se conecta a `http://localhost:11434`, que es el Ollama de la computadora donde corre el comando.

Opciones: `--format esto-realmente-paso|ultimas-horas|pov-historico`, `--duration 75`, `--model qwen2.5:3b`, `--output output`. También podés elegir otro modelo con `--model` o definir `OLLAMA_MODEL`. Para cambiar la dirección del servidor, definí `OLLAMA_URL` (por ejemplo, en PowerShell: `$env:OLLAMA_URL = "http://localhost:11434"`).

## Archivos generados

El resultado queda en `output/<tema>/`:

- `sources.json` y `research.md`: referencias iniciales para verificar.
- `script.json` y `script.txt`: guion dividido en escenas.
- `visuals.json`: prompts de imagen y animación por escena.
- `production_kit.md`: narración, rótulos, prompts y pasos para llevar las escenas a Gemini, Qwen y Clipchamp.
- `metadata.json`: modelo y estado del borrador.

## Flujo de trabajo

1. Buscar referencias iniciales en Wikipedia en español e inglés.
2. Usar el modelo local de Ollama para redactar y estructurar el guion.
3. Validar formato, duración, continuidad temporal y referencias citadas.
4. Preparar un prompt de imagen y uno de animación por escena, respetando el estilo visual del canal.
5. Revisar los datos y usar `production_kit.md` para producir manualmente las imágenes, animaciones, voz, subtítulos y edición.

Las referencias son pistas de investigación, no una verificación editorial. Revisá las páginas originales y las fuentes que citan antes de publicar. La validación automática comprueba estructura y referencias, pero no puede probar por sí sola que cada afirmación del guion sea verdadera.

Gemini, Qwen y Clipchamp no se automatizan en este MVP: el kit prepara sus insumos y las instrucciones de montaje. Sus funciones y límites gratuitos dependen de cada servicio, cuenta y región. Antes de publicar, comprobá la licencia de música y recursos, y que las recreaciones sintéticas no se confundan con material de archivo auténtico.

## Estructura

```text
accounts/archivo_imposible.json
schemas/script.schema.json
schemas/visuals.schema.json
prompts/                     # reglas editoriales
src/content_factory/          # CLI, adaptador de Ollama, búsqueda y validación
output/                       # resultados, ignorados por git
```

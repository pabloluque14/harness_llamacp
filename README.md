# Harness Llama.cpp 🦙🤖

Banco de pruebas multi-agente para LLMs locales servidos con **`llama-server`** ([llama.cpp](https://github.com/ggml-org/llama.cpp)): tool calling, decodificación especulativa MTP, sandboxes con permisos y orquestación con LangGraph + **MCP**.

Modelo por defecto: **Gemma 4 12B IT QAT** (`unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL`), expuesto como API compatible con OpenAI en `http://localhost:8080/v1`.

---

## ⚡ Arranque rápido

```bash
# Terminal 1: servidor del modelo (déjalo corriendo)
llama-server \
  -hf unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL \
  --alias gemma-4-12b-it-qat \
  --port 8080 \
  --jinja \
  --spec-type draft-mtp --spec-draft-n-max 4 \
  -ngl 999 -fa on \
  -c 32768

# Terminal 2: comprobar y lanzar un experimento
curl -s localhost:8080/health          # → {"status":"ok"}
./env_agentes/bin/python prueba.py     # smoke test de tool calling
```

La primera vez descarga unos 7 GB. Después arranca en unos 15 s desde la caché.

---

## 🦙 Guía del servidor (`llama-server`)

### Instalar / actualizar llama.cpp

```bash
brew install llama.cpp        # primera vez
brew upgrade llama.cpp        # actualizar el binario
llama-server --version        # comprobar versión
```

### Qué hace cada flag

| Flag | Para qué |
|------|----------|
| `-hf repo:quant` | Descarga el modelo desde Hugging Face (o lo usa de la caché). Si el repo los tiene, baja también el **draft MTP** (`mtp-*.gguf`) y el **mmproj** (visión/audio). |
| `--alias gemma-4-12b-it-qat` | Nombre que devuelve `/v1/models`. Coincide con el `model=` que usan los scripts. |
| `--port 8080` | Fija el puerto. **Importante**: llama.cpp avisa de que el puerto por defecto pasará a `9931` en una versión futura, y los scripts apuntan a `8080`. |
| `--jinja` | Usa la plantilla de chat del modelo. **Imprescindible para el tool calling.** |
| `--spec-type draft-mtp --spec-draft-n-max 4` | Decodificación especulativa con el draft MTP (hasta 4 tokens por paso). |
| `-ngl 999` | Todas las capas en la GPU (Metal). |
| `-fa on` | Flash Attention. |
| `-c 32768` | Ventana de contexto (32k tokens). Súbela si los agentes se quedan sin contexto y hay RAM de sobra. |

Opcionales útiles:
- `--offline`: no consulta Hugging Face y usa solo la caché (arranque sin red).
- `--no-mmproj`: no carga el proyector multimodal (ahorra memoria si solo usas texto).
- `--host 0.0.0.0`: exponer en la red local. Añade `--api-key <clave>`, porque por defecto no hay autenticación y CORS acepta cualquier origen.

### Comprobar que funciona

```bash
curl -s localhost:8080/health                    # {"status":"ok"} cuando el modelo está cargado
curl -s localhost:8080/v1/models | python3 -m json.tool
```

La interfaz web de chat está en <http://localhost:8080>.

### Parar el servidor

`Ctrl+C` en su terminal. Si quedó en segundo plano: `pkill llama-server`.

---

## 📦 Gestión de modelos

### Dónde están

`-hf` guarda los modelos en la **caché de Hugging Face**:

```text
~/.cache/huggingface/hub/models--unsloth--gemma-4-12B-it-qat-GGUF/snapshots/<commit>/
├── gemma-4-12B-it-qat-UD-Q4_K_XL.gguf   # modelo principal
├── mtp-gemma-4-12B-it.gguf              # draft para MTP
└── mmproj-BF16.gguf                     # proyector multimodal
```

(Se puede cambiar con la variable `HF_HOME`.)

### Listar

```bash
llama-server --cache-list      # modelos que llama.cpp ve en caché
hf cache ls                    # tamaño y fecha de cada repo
```

### Actualizar un modelo

**Reinicia el servidor sin `--offline`.** En cada arranque, `-hf` consulta la lista de ficheros actual del repo en Hugging Face y, si hay una revisión nueva, la descarga a un snapshot nuevo antes de cargarla. No hay que hacer nada más.

Para descargar sin arrancar el servidor (por ejemplo, de noche):

```bash
hf download unsloth/gemma-4-12B-it-qat-GGUF \
  --include "*UD-Q4_K_XL*" "mtp-*" "mmproj-BF16*"
```

Las revisiones antiguas se quedan en disco. Para limpiarlas:

```bash
hf cache prune
```

### Cambiar a otro modelo

1. Arranca con otro repo/quant: `-hf <usuario>/<repo>-GGUF:<QUANT>` (por ejemplo `:Q4_K_M` o `:Q8_0`).
2. Ajusta `--alias` y el `model=` de los scripts (`ChatOpenAI(model=...)`) para que coincidan.
3. `--spec-type draft-mtp` solo funciona si el repo incluye un `mtp-*.gguf`. Si no lo tiene, quita ese flag.

### Borrar un modelo

```bash
hf cache rm model/unsloth/gemma-4-12B-it-qat-GGUF
```

---

## 🐍 Entorno Python

Python 3.11+. Además hacen falta Node (`npx`, para el servidor MCP) y `git`.

```bash
uv venv env_agentes --python python3.11
source env_agentes/bin/activate
uv pip install deepagents langchain langchain-openai langgraph mcp flask pytest
```

Todos los scripts se conectan con la misma configuración:

```python
ChatOpenAI(model="gemma-4-12b-it-qat", base_url="http://localhost:8080/v1", api_key="local-no-needed")
```

---

## 🧪 Experimentos

Todos requieren el servidor arrancado. Ejecútalos desde la raíz del repo:

| Comando | Qué hace | Dónde escribe |
|---------|----------|---------------|
| `./env_agentes/bin/python prueba.py` | Smoke test de tool calling (`ping`) | nada |
| `./env_agentes/bin/python prueba2.py` | Agente enjaulado que lee/escribe ficheros | `sandbox/` |
| `./env_agentes/bin/python prueba3.py` | Un solo agente en bucle TDD con reintentos | `sandbox/` |
| `./env_agentes/bin/python agentes_run.py` | Equipo PM → Coder → Tester con `LocalShellBackend` (shell) | `sandbox/` |
| `./env_agentes/bin/python equipo_deepagents_1.py` | Equipo con `FilesystemBackend` y permisos reales: el coder escribe, el tester solo lee + `run_pytest` | `sandbox/` |
| `./env_agentes/bin/python app_nocturno.py` | Factoría LangGraph + MCP Filesystem Server (`npx`) con PM, Dev, QA y commits git | `recetas_web/` (se crea sola) |

Validar el código generado en el sandbox:

```bash
cd sandbox && ../env_agentes/bin/pytest -v
```

`antiguo/` guarda una versión anterior de la app generada, solo como referencia.

---

## 🩺 Problemas frecuentes

| Síntoma | Causa / solución |
|---------|------------------|
| `Connection refused` en los scripts | El servidor no está arrancado o está en otro puerto: `curl localhost:8080/health`. |
| El modelo no llama a las herramientas | Falta `--jinja` al arrancar. |
| `GraphRecursionError` | El agente agotó `recursion_limit` (50–100 según el script). Sube el valor en el script o simplifica la tarea. |
| Se queda sin contexto / respuestas cortadas | Sube `-c` (por ejemplo `65536`) si la memoria lo permite. |
| Arranque lento o fallo sin red | Usa `--offline` para cargar desde la caché. |
| Warnings `control-looking token ... <\|tool_response>` o `Gemma4Assistant requires ctx_other` al arrancar | Normales con Gemma 4 + MTP. Se pueden ignorar. |

---

## 🗂️ Estructura

```text
harness_llamacp/
├── prueba.py, prueba2.py, prueba3.py   # Experimentos de un solo agente
├── agentes_run.py                      # Equipo DeepAgents con shell
├── equipo_deepagents_1.py              # Equipo DeepAgents con permisos por rol
├── app_nocturno.py                     # LangGraph + MCP
├── sandbox/                            # Jaula donde trabajan los agentes
├── antiguo/                            # Versión anterior de la app generada
├── AGENTS.md                           # Guía para agentes de código
└── docs/agents/                        # Config de las skills (issues, triage, dominio)
```

## 🛠️ Skills de agente

Configuradas en `AGENTS.md` y `docs/agents/`:
- **Issues**: markdown local en `.scratch/<feature>/` (`/to-spec`, `/to-tickets`, `/triage`).
- **Triage**: etiquetas por defecto (`needs-triage`, `ready-for-agent`, …).
- **Metodología**: `/tdd`, `/diagnosing-bugs`, `/code-review`, `/grilling`.

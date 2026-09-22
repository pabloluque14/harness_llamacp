# Harness Llama.cpp 🦙🤖

Banco de pruebas y fábrica multi-agente para experimentación con modelos de lenguaje locales (LLMs) servidos a través de **`llama-server`** ([llama.cpp](https://github.com/ggerganov/llama.cpp)) con soporte para Function Calling / Tool Use, decodificación especulativa (MTP) y protocolos estándar como **MCP** (*Model Context Protocol*).

---

## 🎯 Objetivo

Este repositorio evalúa y compara diferentes paradigmas de desarrollo autónomo de software con LLMs locales (como `Gemma 4 12B IT QAT`):

1. **Agentes Reactivos y Tool Calling Básico**: Evaluación de prompts, invocación de herramientas y límites de recursión.
2. **DeepAgents con Jaula de Sandbox**: Aislamiento de ejecución y control granular de permisos (lectura/escritura) entre subagentes de desarrollo y control de calidad.
3. **Grafos Asíncronos (LangGraph + MCP)**: Orquestación de arquitecturas complejas de ingeniería Full-Stack conectando herramientas oficiales del ecosistema MCP.
4. **Habilidades de Ingeniería (Matt Pocock Skills)**: Integración de estándares profesionales para agentes (`grill-me`, `tdd`, `code-review`, especificaciones y seguimiento local en Markdown).

---

## 🏗️ Estructura del Repositorio

```text
harness_llamacp/
├── AGENTS.md                  # Directrices de ingeniería para agentes en el repo
├── README.md                  # Documentación del proyecto
├── agentes_run.py             # Equipo DeepAgents con LocalShellBackend (PM -> Coder -> Tester)
├── equipo_deepagents_1.py     # Equipo DeepAgents con FilesystemBackend y permisos estrictos
├── app_nocturno.py            # Factoría Full-Stack con LangGraph + MCP Filesystem Server
├── prueba.py                  # Test unitario de Tool Calling (ping)
├── prueba2.py                 # Agente enjaulado con capacidad de lectura y escritura
├── prueba3.py                 # Flujo TDD en agente único con bucle de reintentos
├── sandbox/                   # Espacio de trabajo aislado donde operan los agentes
│   ├── app.py                 # Aplicación Flask generada en el sandbox
│   └── test_app.py            # Suite de pruebas Pytest generadas
└── docs/                      # Documentación del repositorio
    └── agents/
        ├── domain.md          # Estructura de dominio y ADRs
        └── issue-tracker.md   # Convenciones de seguimiento de tareas (.scratch/)
```

---

## 🚀 Requisitos Previos

### 1. Servidor Local `llama-server`
El harness está optimizado para conectarse a un endpoint compatible con la API de OpenAI en `http://localhost:8080/v1`. 

Ejemplo de arranque con decodificación especulativa MTP y contexto extendido:

```bash
llama-server \
  -hf unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL \
  --jinja \
  --spec-type draft-mtp --spec-draft-n-max 4 \
  -ngl 999 -fa on \
  -c 32768
```

### 2. Entorno Python
Recomendado Python 3.11+. Para instalar las dependencias con [uv](https://docs.astral.sh/uv/) o pip:

```bash
# Crear entorno virtual
uv venv env_agentes --python python3.11
source env_agentes/bin/activate

# Instalar dependencias
uv pip install deepagents langchain langchain-openai langgraph mcp flask pytest
```

---

## 🧪 Ejecución de Experimentos

### 1. Equipo DeepAgents con separación estricta de roles
Ejecuta un Project Manager que descompone tareas, delega la escritura a un programador (con permisos de lectura/escritura) y valida con un tester (aislado en solo lectura):

```bash
./env_agentes/bin/python equipo_deepagents_1.py
```

### 2. Factoría Autónoma LangGraph + Servidor MCP
Orquesta un flujo asíncrono con `npx @modelcontextprotocol/server-filesystem` conectando PM, Desarrollador, QA y control de versiones Git:

```bash
./env_agentes/bin/python app_nocturno.py
```

### 3. Ejecutar los tests del Sandbox
Para validar que el código generado en el sandbox cumple con la suite de pruebas:

```bash
cd sandbox
../env_agentes/bin/pytest -v
```

---

## 🛠️ Habilidades de Agente (Matt Pocock Skills)

El repositorio cuenta con directrices configuradas en `AGENTS.md` y `docs/agents/`:
- **`/grill-me`**: Entrevista iterativa para poner a prueba decisiones de diseño y arquitectura.
- **`/tdd`**: Enfoque *Test-Driven Development* estricto (Red-Green-Refactor).
- **`/to-spec` & `/to-tickets`**: Generación de especificaciones y desglose de tareas en ficheros locales dentro de `.scratch/`.

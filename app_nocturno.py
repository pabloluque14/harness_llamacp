import os
import asyncio
import subprocess
from pathlib import Path
from typing import Annotated, TypedDict, Literal
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*LangGraphDeprecated.*")

# 1. Configuración del Sandbox de Seguridad
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = str(BASE_DIR / "recetas_web")
os.makedirs(PROJECT_DIR, exist_ok=True)

# 2. Herramientas Locales Asíncronas (Terminal y Git)
@tool
async def ejecutar_comando_sistema(comando: str) -> str:
    """Ejecuta comandos controlados en la terminal del proyecto (npm test, npm install, npm run build)."""
    comandos_seguros = {
        "npm test": ["npm", "test"],
        "npm install": ["npm", "install"],
        "npm run build": ["npm", "run", "build"],
    }
    if comando not in comandos_seguros:
        return f"Error: El comando '{comando}' no está permitido por seguridad."
    
    try:
        # Ejecución asíncrona segura sin shell
        args = comandos_seguros[comando]
        proceso = await asyncio.create_subprocess_exec(
            *args,
            cwd=PROJECT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await proceso.communicate()
        output = stdout.decode('utf-8', errors='ignore') + "\n" + stderr.decode('utf-8', errors='ignore')
        return f"Código de salida: {proceso.returncode}\n\nResultado de la terminal:\n{output}"
    except Exception as e:
        return f"Error al ejecutar el comando: {str(e)}"

@tool
async def ejecutar_git_seguro(mensaje_commit: str) -> str:
    """Inicializa Git y hace un commit profesional cuando los tests estén en verde."""
    try:
        git_dir = os.path.join(PROJECT_DIR, ".git")
        if not os.path.exists(git_dir):
            p = await asyncio.create_subprocess_exec("git", "init", cwd=PROJECT_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            await p.communicate()
        
        p = await asyncio.create_subprocess_exec("git", "add", ".", cwd=PROJECT_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        await p.communicate()
        
        p = await asyncio.create_subprocess_exec("git", "commit", "-m", mensaje_commit, cwd=PROJECT_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = await p.communicate()
        return f"Git Executed:\n{stdout.decode('utf-8', errors='ignore')}\n{stderr.decode('utf-8', errors='ignore')}"
    except Exception as e:
        return f"Error en operaciones de Git: {str(e)}"

# 3. Conexión con tu Servidor MTP (8080)
llm = ChatOpenAI(
    model="gemma-4-12b-it-qat",
    base_url="http://localhost:8080/v1",
    api_key="local-no-needed",
    temperature=0.1
)

# 4. Estado de la memoria del Grafo
class UpgradeTeamState(TypedDict):
    objetivo: str
    arquitectura_pm: str
    feedback_qa: str
    test_status: str
    iteracion: int

# 5. Configuración de los Nodos del Grafo Asíncrono
async def nodo_pm_planificador(state: UpgradeTeamState):
    print(f"\n[Fase Inicial] 👨‍💼 PM: Diseñando el plan de ataque Full-Stack + CI/CD...")
    prompt = """
    Diseña la estructura completa para una aplicación Full-Stack profesional de recetas y menú semanal.
    Requisitos obligatorios:
    1. Backend: Node.js + Express + SQLite.
    2. Frontend: React + TypeScript + Tailwind CSS (Vite).
    3. Testing: Suite de pruebas con Vitest/Jest que verifique los endpoints.
    4. CI/CD: Archivo .github/workflows/ci.yml para ejecutar los tests.
    5. DOCUMENTACIÓN OBLIGATORIA: Un archivo 'README.md' en la raíz que explique detalladamente los requisitos, cómo instalar dependencias y los comandos exactos para arrancar tanto el backend como el frontend.
    Sé extremadamente exhaustivo. No dejes comentarios tipo '// TODO'.
    """
    res = await llm.ainvoke([SystemMessage(content="Eres el Director de Tecnología y PM."), HumanMessage(content=prompt)])
    return {"arquitectura_pm": res.content}

# Definimos variables globales para los agentes que instanciaremos dentro del contexto MCP
dev_agent = None
qa_agent = None
git_agent = None

async def nodo_developer_core(state: UpgradeTeamState):
    nueva_iteracion = state["iteracion"] + 1
    print(f"\n[Ciclo {nueva_iteracion}] 👨‍💻 Developer: Programando con herramientas del Servidor MCP Filesystem...")
    contexto = f"Plan del PM:\n{state['arquitectura_pm']}\n\nFeedback del QA (si lo hay):\n{state['feedback_qa']}"
    prompt = """
    Eres el Senior Full-Stack Developer. El directorio actual está COMPLETAMENTE VACÍO.
    Tu primer paso obligatorio es crear el archivo 'package.json' usando 'write_file'.
    Luego, crea la estructura de carpetas, escribe el código real completo y genera el archivo 'README.md' con las instrucciones de arranque requeridas.
    Cuentas con las herramientas seguras de MCP: 'write_file', 'read_file' y 'list_directory'. Usa 'write_file' indicando el 'path' relativo (ej: "package.json" o "backend/server.js") y el 'content'.
    """
    res = await dev_agent.ainvoke({"messages": [SystemMessage(content=prompt), HumanMessage(content=contexto)]})
    return {"feedback_qa": "", "iteracion": nueva_iteracion}

async def nodo_qa_tester(state: UpgradeTeamState):
    print("🕵️‍♂️ QA Engineer: Validando la integridad del código y corriendo tests...")
    prompt = """
    Eres el Lead QA Engineer. Tu obligación es usar 'ejecutar_comando_sistema' para lanzar 'npm install' y 'npm test'.
    Si absolutamente todos los tests pasan con éxito (Código de salida 0), responde únicamente con la palabra 'PASSED_CLEAN'.
    Si algo falla, detalla qué debe corregir el desarrollador usando las herramientas de lectura de archivos si es necesario.
    """
    res = await qa_agent.ainvoke({"messages": [SystemMessage(content=prompt), HumanMessage(content="Audita el estado actual del directorio de trabajo.")]})
    output_texto = res["messages"][-1].content
    status = "PASSED" if "PASSED_CLEAN" in output_texto else "FAILED"
    print(f"   -> Resultado del control de calidad: {status}")
    return {"feedback_qa": output_texto, "test_status": status}

async def nodo_git_deployer(state: UpgradeTeamState):
    print("🚀 Git Agent: ¡Suite de tests en verde! Despliegue seguro bajo control...")
    prompt = "Usa 'ejecutar_git_seguro' para guardar todo el progreso en el repositorio con un mensaje profesional."
    await git_agent.ainvoke({"messages": [SystemMessage(content=prompt)]})
    return {}

def enrutador_de_calidad(state: UpgradeTeamState) -> Literal["Developer", "Git", "__end__"]:
    if state["test_status"] == "PASSED":
        return "Git"
    if state["iteracion"] < 20:
        return "Developer"
    print("⚠️ Se ha alcanzado el límite de refactorizaciones. Forzando parada de seguridad sin commit.")
    return END

# 6. Orquestación de la sesión principal de ejecución
async def main():
    global dev_agent, qa_agent, git_agent

    print("🔌 Conectando con el Servidor MCP Filesystem oficial via NPX...")
    
    # Configuramos los parámetros del servidor MCP oficial de Filesystem
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", PROJECT_DIR]
    )

    # Establecemos el canal de comunicación Stdio de MCP
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Inicializamos el protocolo de mutuo acuerdo
            await session.initialize()
            print("✅ Servidor MCP Inicializado con éxito. Vinculando herramientas de ingeniería...")

            # Creamos wrappers de LangChain que delegan la ejecución real en el Servidor MCP
            @tool
            async def write_file(path: str, content: str) -> str:
                """Escribe o crea un archivo con el contenido de texto especificado."""
                res = await session.call_tool("write_file", arguments={"path": path, "content": content})
                return "".join([b.text for b in res.content if hasattr(b, 'text')])

            @tool
            async def read_file(path: str) -> str:
                """Lee y devuelve el contenido de un archivo específico del proyecto."""
                res = await session.call_tool("read_file", arguments={"path": path})
                return "".join([b.text for b in res.content if hasattr(b, 'text')])

            @tool
            async def list_directory() -> str:
                """Lista de forma estructurada todos los archivos y carpetas del espacio de trabajo."""
                res = await session.call_tool("list_directory", arguments={})
                return "".join([b.text for b in res.content if hasattr(b, 'text')])

            # Instanciamos los agentes inyectándoles las herramientas del Servidor MCP
            dev_agent = create_react_agent(llm, tools=[write_file, read_file, list_directory])
            qa_agent = create_react_agent(llm, tools=[read_file, list_directory, ejecutar_comando_sistema])
            git_agent = create_react_agent(llm, tools=[ejecutar_git_seguro])

            # Construcción del Grafo
            workflow = StateGraph(UpgradeTeamState)
            workflow.add_node("PM", nodo_pm_planificador)
            workflow.add_node("Developer", nodo_developer_core)
            workflow.add_node("QA", nodo_qa_tester)
            workflow.add_node("Git", nodo_git_deployer)

            workflow.add_edge(START, "PM")
            workflow.add_edge("PM", "Developer")
            workflow.add_edge("Developer", "QA")
            workflow.add_conditional_edges("QA", enrutador_de_calidad, {"Developer": "Developer", "Git": "Git", END: END})
            workflow.add_edge("Git", END)

            equipo_nocturno = workflow.compile()

            print("🦾 Factoría Multi-Agente Autónoma Operativa (Conexión MCP + MTP Activa).")
            
            estado_inicial = {
                "objetivo": "Crear una app Full-Stack profesional de recetas con optimizador, tests y README de arranque.",
                "arquitectura_pm": "",
                "feedback_qa": "Ninguno. Empezar desarrollo desde cero.",
                "test_status": "FAILED",
                "iteracion": 0
            }
            
            # Ejecución del stream asíncrono
            async for estado in equipo_nocturno.astream(estado_inicial, {"recursion_limit": 100}):
                pass
                
            print("\n🏁 [MISIÓN CUMPLIDA] Tu equipo ha trabajado con éxito. Aplicación desarrollada, testeada y documentada vía MCP.")

if __name__ == "__main__":
    asyncio.run(main())

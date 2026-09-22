"""
PoC deepagents: equipo PM -> coder -> tester con separacion REAL de roles.

Requisitos EN TU ENTORNO (no en el sandbox):
    pip install deepagents langchain-openai flask pytest
y tu servidor local sirviendo el modelo en http://localhost:8080/v1

Claves del refactor:
  - Backend = FilesystemBackend (SIN shell). Esto es lo que permite usar
    'permissions': los permisos NO se aplican a backends con execute.
  - coder  -> permiso de escritura: escribe la app y los tests, pero NO testea.
  - tester -> solo lectura + una tool acotada 'run_pytest': testea pero NO escribe.
  - Observabilidad: se hace stream con subgraphs=True para ver "la cocina"
    (todos, delegaciones, salida de pytest, reintentos), no solo el mensaje final.
  - El servidor nunca se arranca: los tests usan test_client (en proceso).

llama-server \
  -hf unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL \
  --jinja \
  --spec-type draft-mtp --spec-draft-n-max 4 \
  -ngl 999 -fa on \
  -c 32768

"""

import subprocess
from pathlib import Path
from collections import defaultdict

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

from deepagents import create_deep_agent, FilesystemPermission
from deepagents.backends import FilesystemBackend

# --- Sandbox -----------------------------------------------------------------
SANDBOX = Path(__file__).resolve().parent / "sandbox"
SANDBOX.mkdir(parents=True, exist_ok=True)

# --- Modelo local ------------------------------------------------------------
llm = ChatOpenAI(
    model="gemma-4-12b-it-qat",
    base_url="http://localhost:8080/v1",
    api_key="local-no-needed",
    temperature=0.8,          # recomendado
    top_p=0.95,               # valor oficial HF
    extra_body={"top_k": 64}, # top_k oficial HF (va por extra_body)
)

# --- Config B: HF "por el libro" (general purpose) ---
# llm = ChatOpenAI(
#     model="gemma-4-12b-it-qat", base_url="http://localhost:8080/v1",
#     api_key="local-no-needed",
#     temperature=1.0, top_p=0.95, extra_body={"top_k": 64},
# )

# --- Backend SIN ejecucion (requisito para que 'permissions' sea valido) -----
# FilesystemBackend escribe en disco real bajo root_dir; virtual_mode=True da
# rutas virtuales limpias (/app.py -> SANDBOX/app.py) para los globs de permisos.
backend = FilesystemBackend(root_dir=str(SANDBOX), virtual_mode=True)

# --- Permisos reutilizables (primer match gana; por defecto: permitido) ------
SOLO_LECTURA = [
    FilesystemPermission(operations=["write"], paths=["/**"], mode="deny"),
]
LECTURA_Y_ESCRITURA = [
    FilesystemPermission(operations=["read", "write"], paths=["/**"], mode="allow"),
]


# --- Tool acotada para el tester (en vez de shell libre) ---------------------
@tool
def run_pytest() -> str:
    """Ejecuta 'pytest -q' sobre el proyecto del sandbox y devuelve la salida.
    No recibe rutas: siempre corre en el directorio del proyecto."""
    proc = subprocess.run(
        ["pytest", "-q"],
        cwd=str(SANDBOX),
        capture_output=True,
        text=True,
        timeout=120,
    )
    salida = (proc.stdout or "") + (proc.stderr or "")
    estado = "PASS" if proc.returncode == 0 else "FAIL"
    return f"[{estado}] exit={proc.returncode}\n{salida[-4000:]}"


# --- Subagentes con roles separados de verdad --------------------------------
coder = {
    "name": "coder",
    "description": "Escribe y edita el codigo de la app y sus tests en archivos.",
    "system_prompt": (
        "Eres programador. Implementa con write_file/edit_file en el sandbox "
        "(usa rutas como /app.py y /test_app.py). Escribe TANTO la app Flask "
        "COMO los tests pytest (test_app.py) que usen test_client. Codigo simple "
        "y funcional. NO ejecutes tests: de eso se encarga el tester."
    ),
    "permissions": LECTURA_Y_ESCRITURA,
}
tester = {
    "name": "tester",
    "description": "Corre pytest sobre el codigo y reporta PASS/FAIL con errores.",
    "system_prompt": (
        "Eres QA. Ejecuta los tests con la herramienta run_pytest (no recibe "
        "rutas). Devuelve PASS o FAIL con los errores exactos. NO modifiques "
        "codigo: no tienes permiso de escritura."
    ),
    "tools": [run_pytest],
    "permissions": SOLO_LECTURA,
}

# --- Project Manager (orquesta, no programa) ---------------------------------
PM = """Eres el Project Manager de un equipo. Ante un objetivo:
1. Descompon el trabajo en tareas (write_todos).
2. Delega la implementacion en el subagente 'coder' (tool task).
3. Pide al subagente 'tester' que valide.
4. Si el tester reporta FAIL, vuelve a delegar en 'coder' con el error concreto. Max 3 ciclos.
5. Termina con un resumen de lo construido y el estado de los tests.
Trabaja solo en el sandbox. Tu no escribes codigo: delegas."""

agent = create_deep_agent(
    model=llm,
    backend=backend,
    subagents=[coder, tester],
    system_prompt=PM,
    permissions=SOLO_LECTURA,  # el PM orquesta; el unico que escribe es el coder
)

# --- Objetivo ----------------------------------------------------------------
objetivo = (
    "Objetivo: una web Flask para gestionar recetas y planificar el menu "
    "semanal, CON interfaz grafica. Recetas en memoria (sin BD), cada una con "
    "nombre, ingredientes y pasos. "
    "Vista principal tipo CALENDARIO: una cuadricula con los 7 dias "
    "(lunes-domingo) y, para cada dia, dos huecos: 'mediodia' y 'cena'. Cada "
    "hueco muestra la receta asignada a ese dia y turno (o queda vacio si no "
    "hay). Renderiza HTML (puedes usar render_template_string para no depender "
    "de una carpeta de plantillas) con algo de CSS para que se vea como un "
    "calendario en cuadricula. "
    "Rutas: pagina del calendario semanal (vista principal '/'), listar recetas, "
    "anadir receta, borrar receta y asignar una receta a un (dia, turno) donde "
    "turno es 'mediodia' o 'cena'. "
    "Tests pytest con test_client que cubran: anadir/listar/borrar recetas, "
    "asignar una receta a un dia y turno, y que la pagina del calendario "
    "responda 200 y muestre la receta asignada en el hueco correcto. "
    "'Funcionando' = los tests pasan en verde con test_client; NO arranques el "
    "servidor (nada de 'flask run' ni 'python app.py')."
)

# --- Ejecucion viendo lo que pasa por dentro ---------------------------------
# 'Max 3 ciclos' es una instruccion (blanda). El corte DURO es recursion_limit.
payload = {"messages": [{"role": "user", "content": objetivo}]}
config = {"recursion_limit": 100}  # la delegacion gasta mas pasos

vistos = defaultdict(int)
mensajes_pm = []
for ns, estado in agent.stream(
    payload, config=config, stream_mode="values", subgraphs=True
):
    etiqueta = "/".join(str(x) for x in ns) if ns else "PM"
    mensajes = estado.get("messages", [])
    for m in mensajes[vistos[ns]:]:           # imprime solo lo nuevo de cada nivel
        print(f"\n-- [{etiqueta}] " + "-" * 40)
        m.pretty_print()
    vistos[ns] = len(mensajes)
    if not ns:                                # estado de nivel PM (raiz)
        mensajes_pm = mensajes

print("\n\n===== RESUMEN FINAL (PM) =====")
print(mensajes_pm[-1].content if mensajes_pm else "(sin mensajes)")

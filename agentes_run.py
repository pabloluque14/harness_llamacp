from pathlib import Path
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent
from deepagents.backends.local_shell import LocalShellBackend

SANDBOX = Path(__file__).resolve().parent / "sandbox"
SANDBOX.mkdir(parents=True, exist_ok=True)


# --- Config A: afinada para agente/código (mi recomendación) ---
llm = ChatOpenAI(
    model="gemma-4-12b-it-qat",
    base_url="http://localhost:8080/v1",
    api_key="local-no-needed",
    temperature=0.2,          # determinista pero no rígido
    top_p=0.95,               # valor oficial HF
    extra_body={"top_k": 64}, # top_k oficial HF (va por extra_body)
)

# --- Config B: HF "por el libro" (general purpose) ---
# llm = ChatOpenAI(
#     model="gemma-4-12b-it-qat", base_url="http://localhost:8080/v1",
#     api_key="local-no-needed",
#     temperature=1.0, top_p=0.95, extra_body={"top_k": 64},
# )

print(">> probando el modelo...", flush=True)
print(llm.invoke("Responde solo: ok").content, flush=True)


backend = LocalShellBackend(root_dir=str(SANDBOX), virtual_mode=True,
                            inherit_env=True, timeout=120)

coder = {
    "name": "coder",
    "description": "Escribe y edita el código de la aplicación en archivos.",
    "system_prompt": ("Eres programador. Implementa con write_file/edit_file. "
                      "Código simple y funcional. NO ejecutes tests, solo escribe código."),
}
tester = {
    "name": "tester",
    "description": "Corre pytest sobre el código y reporta PASS/FAIL con errores.",
    "system_prompt": ("Eres QA. Ejecuta 'pytest -q' con execute. Devuelve PASS o FAIL "
                      "con los errores exactos. NO modifiques código."),
}

PM = """Eres el Project Manager de un equipo. Ante un objetivo:
1. Descompón el trabajo en tareas (write_todos).
2. Delega la implementación en el subagente 'coder' (tool task).
3. Pide al subagente 'tester' que valide.
4. Si el tester reporta FAIL, vuelve a delegar en 'coder' con el error concreto. Máx 3 ciclos.
5. Termina con un resumen de lo construido y el estado de los tests.
Trabaja solo en el sandbox."""

agent = create_deep_agent(model=llm, backend=backend,
                          subagents=[coder, tester], system_prompt=PM)

r = agent.invoke(
    {"messages": [{"role": "user", "content":
        "Objetivo: una web Flask de lista de tareas (to-do). Rutas para listar, "
        "añadir y borrar tareas (en memoria, sin BD). Tests pytest con test_client. "
        "Déjalo funcionando y con los tests en verde."}]},
    config={"recursion_limit": 100},   # más alto: la delegación gasta más pasos
)
print(r["messages"][-1].content)
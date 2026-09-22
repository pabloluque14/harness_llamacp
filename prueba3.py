from pathlib import Path
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent
from deepagents.backends.local_shell import LocalShellBackend

SANDBOX = Path(__file__).resolve().parent / "sandbox"
SANDBOX.mkdir(parents=True, exist_ok=True)

llm = ChatOpenAI(model="gemma-4-12b-it-qat", base_url="http://localhost:8080/v1",
                 api_key="local-no-needed", temperature=0.1)

backend = LocalShellBackend(root_dir=str(SANDBOX), virtual_mode=True,
                            inherit_env=True, timeout=120)

CODER_QA = """Eres un programador con disciplina de QA. Tu flujo SIEMPRE es:
1. Escribe el código en archivos (write_file).
2. Escribe tests con pytest usando flask.test_client() (NUNCA lances el servidor).
3. Ejecuta 'pytest -q' con execute.
4. Si falla: lee el error, corrige el archivo, repite. Máximo 3 intentos.
5. Para cuando los tests pasen, o avisa si tras 3 intentos siguen fallando.
Código simple. Trabaja solo dentro del sandbox."""

agent = create_deep_agent(model=llm, backend=backend, system_prompt=CODER_QA)

r = agent.invoke(
    {"messages": [{"role": "user", "content":
        "Haz una web Flask con dos rutas: '/' que devuelva 'Hola Pablo' y "
        "'/saluda/<nombre>' que devuelva 'Hola <nombre>'. Incluye tests pytest "
        "con test_client para ambas rutas y déjalos pasando."}]},
    config={"recursion_limit": 50},   # el bucle gasta varios pasos; subimos el límite
)
print(r["messages"][-1].content)
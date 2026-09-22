from pathlib import Path
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent
from deepagents.backends.local_shell import LocalShellBackend

SANDBOX = Path(__file__).resolve().parent / "sandbox"
SANDBOX.mkdir(parents=True, exist_ok=True)

llm = ChatOpenAI(model="gemma-4-12b-it-qat",
                 base_url="http://localhost:8080/v1",
                 api_key="local-no-needed", temperature=0.1)

backend = LocalShellBackend(
    root_dir=str(SANDBOX),
    virtual_mode=True,    # jaula: el agente NO puede salir del sandbox
    inherit_env=True,     # para que 'execute' vea tu venv (python, flask)
    timeout=120,
)

agent = create_deep_agent(
    model=llm,
    backend=backend,
    system_prompt=("Eres un programador. Trabajas en el sandbox con write_file, "
                   "read_file, ls, edit_file, y execute para comandos. "
                   "Código Python simple y funcional."),
)

r = agent.invoke({"messages": [{"role": "user", "content":
    "Crea app.py con una app Flask mínima: ruta '/' que devuelva 'Hola Pablo'. "
    "Luego haz 'ls' y enséñame app.py con read_file."}]})
print(r["messages"][-1].content)
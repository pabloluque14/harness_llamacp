from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from deepagents import create_deep_agent

llm = ChatOpenAI(
    model="gemma-4-12b-it-qat",
    base_url="http://localhost:8080/v1",
    api_key="local-no-needed",
    temperature=0.1,
)

@tool
def ping(msg: str) -> str:
    """Devuelve pong: <msg>. Sirve para probar tool calling."""
    return f"pong: {msg}"

agent = create_deep_agent(
    model=llm,
    tools=[ping],
    system_prompt="Usa la tool ping cuando te lo pidan.",
)

r = agent.invoke({"messages": [{"role": "user",
                  "content": "Llama a ping con 'hola Pablo'"}]})
print(r["messages"][-1].content)

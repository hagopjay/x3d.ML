from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
class S(TypedDict):
    n:int
def w(s): return {"n":s["n"]+1}
g=StateGraph(S); g.add_node("w",w); g.add_edge(START,"w")
g.add_conditional_edges("w",lambda s:"w" if s["n"]<3 else END)
a=g.compile(checkpointer=MemorySaver())
print(a.invoke({"n":0},{"configurable":{"thread_id":"t"}}))

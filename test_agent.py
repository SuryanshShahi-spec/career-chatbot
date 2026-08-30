import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "Data") not in sys.path:
    sys.path.insert(0, str(ROOT / "Data"))

from Agent.app import build_graph
from langchain_core.messages import HumanMessage

def test_agent():
    print("Building graph...")
    graph = build_graph()
    
    print("\n--- Testing location-based search ---")
    result = graph.invoke({"messages": [HumanMessage(content="Search for Data Scientist jobs in top Indian cities. Keep it brief.")]})
    print(result["messages"][-1].content)
    
    print("\n--- Testing save application ---")
    result = graph.invoke({"messages": [HumanMessage(content="Save that I applied for a Software Engineer position at OpenAI in San Francisco. Notes: Got referral from Sam.")]})
    print(result["messages"][-1].content)
    
    print("\n--- Testing get applications ---")
    result = graph.invoke({"messages": [HumanMessage(content="Show me my saved job applications.")]})
    print(result["messages"][-1].content)

if __name__ == "__main__":
    test_agent()

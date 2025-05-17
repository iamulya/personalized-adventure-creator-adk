# adventure_creator/app.py
from google.adk.agents import Agent
from google.adk.tools import agent_tool, ToolContext, FunctionTool # Added FunctionTool
from pydantic import BaseModel, Field as PydanticField # For input_schema
from .config import MODEL_NAME
from .agents import (
    broad_query_clarifier_agent,
    adventure_map_sequential_orchestrator,
)

# Define an input schema for the AdventureMapSequentialOrchestrator when called as a tool
# This schema should match the input_schema of its *first* sub-agent.
class SequentialOrchestratorInput(BaseModel):
    adventure_description: str = PydanticField(description="The refined adventure description to process.")


# The root_agent uses AgentTool to wrap its sub-agents.
root_agent = Agent(
    name="MainAdventureCoordinator",
    model=MODEL_NAME,
    instruction=f"""You are the main coordinator for creating adventure maps. Your process is:
1.  Take the user's adventure description (a string).
2.  **Call the '{broad_query_clarifier_agent.name}' tool.** Pass the user's original adventure description as the 'user_query' argument (e.g., `'{broad_query_clarifier_agent.name}(user_query="user description")'`). This tool will return a single string: the (potentially) refined query. Let's call this `refined_adventure_description_string`.
3.  **Call the '{adventure_map_sequential_orchestrator.name}' tool.** Pass the `refined_adventure_description_string` from step 2 as the 'adventure_description' argument for this tool (e.g., `'{adventure_map_sequential_orchestrator.name}(adventure_description="refined_description_string")'`). This tool will execute a sequence of internal agents to generate the KML and will return the final KML generation confirmation string.
4.  Present the final string message returned by the '{adventure_map_sequential_orchestrator.name}' tool directly to the user.

Your tools are: '{broad_query_clarifier_agent.name}' and '{adventure_map_sequential_orchestrator.name}'.
Delegate tasks appropriately.
""",
    description="Top-level coordinator: clarifies query, then delegates to a sequential orchestrator for map creation.",
    tools=[
        agent_tool.AgentTool(agent=broad_query_clarifier_agent),
        # When wrapping a SequentialAgent with AgentTool, ADK will try to find an input_schema
        # on the SequentialAgent itself, or pass 'request' by default.
        # To make it work with specific args, the SequentialAgent's *first sub-agent's input_schema*
        # effectively becomes the input_schema for the AgentTool wrapping the SequentialAgent.
        # ADK's AgentTool might not directly support input_schema for SequentialAgent in its constructor.
        # The LLM will need to call it as if its parameters are those of LocationResearchWrapperInput.
        agent_tool.AgentTool(agent=adventure_map_sequential_orchestrator)
    ],
    sub_agents=[]
)

# To make AgentTool work more cleanly with AdventureMapSequentialOrchestrator,
# we can give AdventureMapSequentialOrchestrator an effective input_schema
# by making its first sub-agent (LocationResearchAgentWrapper) define it.
# The AgentTool will pick up the input_schema from the first LlmAgent it encounters
# if the wrapped agent is a composite agent like SequentialAgent.
# This is already done in agents.py by giving LocationResearchAgentWrapper an input_schema.
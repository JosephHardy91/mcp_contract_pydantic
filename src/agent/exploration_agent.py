from .state import GraphDependencies
from pydantic_ai import Agent
from dotenv import load_dotenv
load_dotenv()

def make_agent(tools):
    # if tools:
    #         system_prompt = (
    #             "You are the Exploration Phase. You traverse a strict data graph. "
    #             "Use your unlocked tools to answer the user's query. "
    #             "You MUST ONLY pass exact JSON objects from your verified inventory into your tools. "
    #             "If you have enough information to answer the question, provide the final answer. If you hit a dead end, say so."
    #         )
    # else:
    #     # Force the model to understand it has no tools and must output plain text
    #     system_prompt = (
    #         "You are the Exploration Phase, but currently NO tools are unlocked because "
    #         "no valid entities exist in your inventory. You cannot traverse the graph right now. "
    #         "Respond immediately to the user in plain text explaining that you cannot find or "
    #         "access records for the requested entities."
    #     )
    explorer_agent = Agent(
        'google:gemini-3-flash-preview',
        deps_type=GraphDependencies,
        tools=tools
    )
    return explorer_agent


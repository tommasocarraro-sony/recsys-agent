from typing import Annotated

from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import START
from langgraph.graph import MessagesState, StateGraph
from langgraph.prebuilt import create_react_agent, InjectedState
from langgraph.types import Send, Command

from src.agents.utils import create_agent_envinroment
from src.tools.get_user_history import get_user_history
from src.tools.get_item_info import get_item_info
from src.tools.estimate_like_percentage import estimate_like_percentage
from src.tools.filter_items_by_popularity import filter_items_by_popularity
from src.tools.recommend_items import recommend_items
from src.tools.get_user_info import get_user_info
from src.tools.filter_items_by_attributes import filter_items_by_attributes
from src.tools.semantic_search_items import semantic_search_items

checkpointer = MemorySaver()

create_agent_envinroment()

llm = ChatOllama(
    # model="qwen2.5:72b-instruct-q6_K",
    model="gpt-oss:120b",
    temperature=0,
    base_url="http://localhost:11434"
)

rec_agent = create_react_agent(
    model=llm,
    tools=[get_item_info, recommend_items, get_user_info, filter_items_by_attributes,
           semantic_search_items, filter_items_by_popularity],
    prompt="""
    You are a helpful movie recommendation assistant.

    General rules:
        - Use the provided tools to answer queries; never hallucinate user IDs, tool calls, or results.
        - **BEFORE** calling tools, you **MUST** always outline your plan in numbered steps (Step i: call <tool_name> to <reason>).
        - Never show raw JSON or code.
        - When calling both the popularity filter tool and attribute filter tool, attribute filter tool MUST be the first.
        - To find items similar to a given item, get its description and then perform a semantic search.
        - When recommendations are asked, the recommendation tool **MUST NEVER** be skipped.
        - For mood-based queries (e.g., depressed, happy users), **ALWAYS** use the semantic search tool to find compatible items and then call the recommendation tool.
        - When showing a list of recommended items, **ALWAYS** show both:
            1. The item IDs (e.g., item <item_id>)
            2. Title, description, and other information you might find useful. **THIS IS IMPORTANT** for user experience.
    """,
    name="rec_agent",
)

stats_agent = create_react_agent(
    model=llm,
    tools=[get_item_info, get_user_info, filter_items_by_attributes, semantic_search_items,
           filter_items_by_popularity, estimate_like_percentage],
    prompt="""
    You are a helpful statistics assistant. 

    General rules:
        - Use the provided tools to answer queries; never hallucinate user IDs, tool calls, or results. Never compute statistics on your own.
        - **BEFORE** calling tools, you **MUST** always outline your plan in numbered steps (Step i: call <tool_name> to <reason>).
        - Never show raw JSON or code.
        - When calling both the popularity filter tool and attribute filter tool, attribute filter tool MUST be the first.
        - To find items similar to a given item, get its description and then perform a semantic search.
        - For all queries but percentage ones, **ALWAYS** call the popularity filter tool to get the top 3 popular items and compute statistics on them.
        - For percentage queries, **ALWAYS** pass all the retrieved items to the percentage estimation tool.
        - When retrieving item info, **FOCUS** on the attributes useful for analyzing the statistic.
        - **ALWAYS** provide an analysis of the statistic.
    """,
    name="stats_agent",
)

# todo here I need to pass context to this agent and each agent has to have its own context - full context solution works
# todo test all queries and then think about the different contexts for the different agents
exp_agent = create_react_agent(
    model=llm,
    tools=[get_item_info, get_user_history],
    prompt="""
    You are a helpful agent to explain recommendations.

    Explanation workflow:
    1. get the history of the user;
    2. get information of the items in the history of the user;
    3. get information of the recommended items (given by the supervisor);
    4. explain the similarities between recommended and interacted items.
    """,
    name="exp_agent",
)

retrieval_agent = create_react_agent(
    model=llm,
    tools=[get_item_info, get_user_history, get_user_info],
    prompt="""
    You are a helpful information retrieval agent.

    General rules:
    - When showing a list of items, **ALWAYS** show both:
        1. The item IDs (e.g., item <item_id>)
        2. Title, description, and other information you might find useful. **THIS IS IMPORTANT** for user experience.
    """,
    name="retrieval_agent",
)


def create_task_description_handoff_tool(
        *, agent_name: str, description: str | None = None
):
    name = f"transfer_to_{agent_name}"
    description = description or f"Ask {agent_name} for help."

    @tool(name, description=description)
    def handoff_tool(
            # this is populated by the supervisor LLM
            task_description: Annotated[
                str,
                "Description of what the next agent should do, including all of the relevant context.",
            ],
            # these parameters are ignored by the LLM
            state: Annotated[MessagesState, InjectedState],
    ) -> Command:
        task_description_message = {"role": "user", "content": task_description}
        agent_input = {**state, "messages": [task_description_message]}
        return Command(
            goto=[Send(agent_name, agent_input)],
            graph=Command.PARENT,
        )

    return handoff_tool


assign_to_rec_agent_with_description = create_task_description_handoff_tool(
    agent_name="rec_agent",
    description="Assign task to a recommendation agent.",
)

assign_to_stats_agent_with_description = create_task_description_handoff_tool(
    agent_name="stats_agent",
    description="Assign task to a statistics agent.",
)

assign_to_exp_agent_with_description = create_task_description_handoff_tool(
    agent_name="exp_agent",
    description="Assign task to an explanation agent.",
)

assign_to_retrieval_agent_with_description = create_task_description_handoff_tool(
    agent_name="retrieval_agent",
    description="Assign task to an information retrieval agent.",
)

supervisor_agent_with_description = create_react_agent(
    model=llm,
    tools=[
        assign_to_stats_agent_with_description,
        assign_to_rec_agent_with_description,
        assign_to_exp_agent_with_description,
        assign_to_retrieval_agent_with_description
    ],
    prompt=(
        """You are the supervisor of a recommendation infrastructure.

        The client may ask about:
            - Personalized recommendations for specific users. **HINT**: look for the recommend keyword in the user query.
            - Statistics or insights about the platform (e.g., best genre, ideal duration, percentage of users)
            - Retrieval of users' histories, user/item metadata
            - Explaining recommendations

        General rules:
            - After calling the recommendation agent, **ALWAYS** ask the user whether he/she would like to get an explanation.
            - When calling the explanation agent, you **MUST** pass the IDs of the recommended movies in the task description.
            - Assign work to one agent at a time, do not call agents in parallel.
            - Do not do any work yourself. """
    ),
    name="supervisor",
)


def call_rec_agent(state):
    response = rec_agent.invoke(state)
    return {"messages": response["messages"][-1]}


def call_stats_agent(state):
    response = stats_agent.invoke(state)
    return {"messages": response["messages"][-1]}


def call_exp_agent(state):
    response = exp_agent.invoke(state)
    return {"messages": response["messages"][-1]}


def call_retrieval_agent(state):
    response = retrieval_agent.invoke(state)
    return {"messages": response["messages"][-1]}


supervisor_with_description = (
    StateGraph(MessagesState)
    .add_node(
        supervisor_agent_with_description, destinations=("rec_agent", "stats_agent", "exp_agent", "retrieval_agent")
    )
    .add_node("rec_agent", call_rec_agent)
    .add_node("stats_agent", call_stats_agent)
    .add_node("exp_agent", call_exp_agent)
    .add_node("retrieval_agent", call_retrieval_agent)
    .add_edge(START, "supervisor")
    .add_edge("rec_agent", "supervisor")
    .add_edge("stats_agent", "supervisor")
    .add_edge("exp_agent", "supervisor")
    .add_edge("retrieval_agent", "supervisor")
    .compile(checkpointer=checkpointer)
)

while True:
    user_input = input("User: ")
    if user_input.lower() in ["quit", "exit", "q"]:
        print("Goodbye!")
        break
    result = supervisor_with_description.invoke({
        "messages": [
            {
                "role": "user",
                "content": user_input,
            }
        ]
    }, config={"configurable": {"thread_id": "1"}})

    for m in result["messages"]:
        m.pretty_print()
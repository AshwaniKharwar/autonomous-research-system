from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
from apps.research_agent.prompts import PlannerAgentPrompt
from apps.research_agent.tools import read_file, write_file, list_files, search_web
load_dotenv()


model = ChatGoogleGenerativeAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    model=os.getenv("GEMINI_PLANNER_MODEL"),
)


async def research_planner(query: str) -> str:
    print("research plan generation starting....")
    agent = create_agent(
        model=model,
        tools=[list_files, write_file, read_file, search_web],
        system_prompt=PlannerAgentPrompt.format(USER_QUERY= query)
    )

    result = await agent.ainvoke({
        "messages": [
            ("user", query)
        ]
    })
    return result



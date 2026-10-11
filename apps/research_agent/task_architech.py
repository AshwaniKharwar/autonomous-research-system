from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
from apps.research_agent.prompts import TaskArchitechAgentPrompt
from apps.research_agent.tools import read_file, write_file, create_directory, list_files, search_web
load_dotenv()


model = ChatGoogleGenerativeAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    model=os.getenv("GEMINI_PLANNER_MODEL"),
)


async def task_architech(query: str) -> str:
    print("Creating Tasks....")
    agent = create_agent(
        model=model,
        tools=[list_files, write_file, read_file, create_directory, search_web],
        system_prompt=TaskArchitechAgentPrompt
    )

    result = await agent.ainvoke({
        "messages": [
            ("user", query)
        ]
    })
    return result



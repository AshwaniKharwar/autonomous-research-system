from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os
from apps.research_agent.prompts import ReportWriterAgentPrompt
from apps.research_agent.tools import read_file, write_file, list_files
load_dotenv()


model = ChatGoogleGenerativeAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    model=os.getenv("GEMINI_PLANNER_MODEL"),
)


def _last_text(result: dict) -> str:
    content = result["messages"][-1].content
    if isinstance(content, list):
        return "\n".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return content


async def report_writer() -> str:
    print("Compiling final report....")
    agent = create_agent(
        model=model,
        tools=[list_files, read_file, write_file],
        system_prompt=ReportWriterAgentPrompt,
    )

    result = await agent.ainvoke(
        {
            "messages": [
                (
                    "user",
                    "Compile the final report. Read /research/plan.md, "
                    "/research/tasks.json, and every file in /research/findings/, "
                    "then write /research/report.md.",
                )
            ]
        }
    )
    return _last_text(result)

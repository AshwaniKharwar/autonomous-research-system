import asyncio
from apps.research_agent.dispatcher import dispatch_research
from apps.research_agent.report_writer import report_writer


async def main(query: str):
    # print("Starting research.....")

    # print("Dispatching Tasks....")
    # print(await dispatch_research())

    print("Starting report generation....")
    print(await report_writer())


if __name__ == "__main__":
    query = "How do solid-state batteries differ from lithium-ion, and which companies are closest to mass production?"
    asyncio.run(main(query))

from src.agents.agents import (
    build_search_agent,
    build_scrape_agent,
    writer_chain,
    critic_chain
)


def run_research_pipeline(topic: str) -> dict:
    state = {}

    # Step 1: Search agent
    print("\nStep 1: Searching the web...")

    search_agent = build_search_agent()

    result = search_agent.invoke({
        "messages": [
            ("user", f"Find useful information about {topic}")
        ]
    })

    state["search_results"] = result["messages"][-1].content

    # Step 2: Scraper agent
    print("\nStep 2: Scraping web content...")

    scrape_agent = build_scrape_agent()

    result = scrape_agent.invoke({
        "messages": [
            ("user",
             f"Choose a relevant URL from these search results "
             f"and scrape its content about {topic}:\n"
             f"{state['search_results'][:3000]}")
        ]
    })

    state["scraped_content"] = result["messages"][-1].content

    # Step 3: Writer
    print("\nStep 3: Writing research report...")

    research = (
        f"Search Results:\n{state['search_results']}\n\n"
        f"Scraped Content:\n{state['scraped_content']}"
    )

    state["report"] = writer_chain.invoke({
        "topic": topic,
        "research": research
    })

    # Step 4: Critic
    print("\nStep 4: Reviewing report...")

    state["feedback"] = critic_chain.invoke({
        "report": state["report"]
    })

    print("\nFinal Report:\n")
    print(state["report"])

    print("\nCritic Feedback:\n")
    print(state["feedback"])

    return state

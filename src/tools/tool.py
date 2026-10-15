from langchain.tools import tool
import requests
from dotenv import load_dotenv
import os
from tavily import TavilyClient
from rich import print
from bs4 import BeautifulSoup
from readability import Document
import trafilatura
import re

load_dotenv()
tavily=TavilyClient(api_key=os.getenv("tavily_api_key"))

@tool
def web_search(query: str) -> str:
    """Search the web and return the top 5 results."""
    response = tavily.search(query=query, max_results=5)
    output = []

    for result in response["results"]:
        output.append(
            f"Title: {result['title']}\n"
            f"URL: {result['url']}\n"
            f"Content: {result['content']}"
        )

    return "\n---\n".join(output)


@tool
def scrape_url(url: str) -> str:
    """Extract readable text content from a webpage URL."""
    response = requests.get(
        url,
        timeout=10,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    output = []

    for text in soup.stripped_strings:
        output.append(text)

    return "\n".join(output)

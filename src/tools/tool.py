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
    """Fetch and extract readable text from a webpage."""
    try:
        response = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
                )
            }
        )

        if response.status_code == 404:
            return f"ERROR: The page does not exist (404): {url}"

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for element in soup([
            "script", "style", "nav", "footer",
            "header", "noscript", "svg"
        ]):
            element.decompose()

        text = soup.get_text(separator="\n", strip=True)

        if not text:
            return f"No readable text was found on this page: {url}"

        return text[:15000]

    except requests.exceptions.Timeout:
        return f"ERROR: The website timed out: {url}"

    except requests.exceptions.RequestException as e:
        return f"ERROR: Could not fetch {url}: {e}"

"""
Web tools — search, fetch pages, and global news briefings.
"""

import httpx
import xml.etree.ElementTree as ET
import asyncio
import re
import webbrowser

SEED_FEEDS = [
    'https://feeds.bbci.co.uk/news/world/rss.xml',
    'https://www.cnbc.com/id/100727362/device/rss/rss.html',
    'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
    'https://www.aljazeera.com/xml/rss/all.xml'
]

FINANCE_SEED_FEEDS = [
    'https://www.cnbc.com/id/10000664/device/rss/rss.html',
    'https://feeds.bloomberg.com/markets/news.rss',
    'https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best',
    'https://feeds.marketwatch.com/marketwatch/topstories/',
    'https://rss.nytimes.com/services/xml/rss/nyt/Business.xml',
]


async def fetch_and_parse_feed(client, url):
    try:
        response = await client.get(url, headers={'User-Agent': 'Friday-AI/1.0'}, timeout=5.0)
        if response.status_code != 200:
            return []
        root = ET.fromstring(response.content)
        source_name = url.split('.')[1].upper()
        feed_items = []
        for item in root.findall(".//item")[:5]:
            title = item.findtext("title")
            description = item.findtext("description")
            link = item.findtext("link")
            if description:
                description = re.sub('<[^<]+?>', '', description).strip()
            feed_items.append({
                "source": source_name,
                "title": title,
                "summary": description[:200] + "..." if description else "",
                "link": link
            })
        return feed_items
    except Exception:
        return []


async def get_world_news() -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
        tasks = [fetch_and_parse_feed(client, url) for url in SEED_FEEDS]
        results_of_lists = await asyncio.gather(*tasks)
        all_articles = [item for sublist in results_of_lists for item in sublist]
    if not all_articles:
        return "The global news grid is unresponsive, sir. I'm unable to pull headlines."
    report = ["### GLOBAL NEWS BRIEFING (LIVE)\n"]
    for entry in all_articles[:12]:
        report.append(f"**[{entry['source']}]** {entry['title']}")
        report.append(f"{entry['summary']}")
        report.append(f"Link: {entry['link']}\n")
    return "\n".join(report)


async def get_world_finance_news() -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
        tasks = [fetch_and_parse_feed(client, url) for url in FINANCE_SEED_FEEDS]
        results_of_lists = await asyncio.gather(*tasks)
        all_articles = [item for sublist in results_of_lists for item in sublist]
    if not all_articles:
        return "The financial feeds are unresponsive right now, sir. I can't pull market headlines."
    report = ["### FINANCE BRIEFING (LIVE)\n"]
    for entry in all_articles[:12]:
        report.append(f"**[{entry['source']}]** {entry['title']}")
        report.append(f"{entry['summary']}")
        report.append(f"Link: {entry['link']}\n")
    return "\n".join(report)


async def search_web(query: str) -> str:
    return f"[stub] Search results for: {query}"


async def fetch_url(url: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text[:4000]


async def open_world_monitor() -> str:
    try:
        webbrowser.open("https://worldmonitor.app/")
        return "Displaying the World Monitor on your primary screen now, sir."
    except Exception as e:
        return f"I'm unable to initialize the visual monitor: {str(e)}"


async def open_finance_world_monitor() -> str:
    try:
        webbrowser.open("https://finance.worldmonitor.app/")
        return "Displaying the Finance World Monitor on your primary screen now, sir."
    except Exception as e:
        return f"I'm unable to initialize the finance monitor: {str(e)}"
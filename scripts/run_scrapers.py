import os
import re
import asyncio
from urllib.parse import urljoin, urlparse
from typing import List
from tools.scraping_service import ScrapingService
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import html2text
import argparse
from bs4 import BeautifulSoup

load_dotenv()

SCRAPE_SOURCES = {
    "nba_com": "https://www.nba.com/news",
    "the_ringer": "https://www.theringer.com/nba",
    "action_network": "https://www.actionnetwork.com/nba",
    "clutchpoints": "https://clutchpoints.com/nba/",
}

def _slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9\-_]+", "-", text.strip().lower())
    text = re.sub(r"-+", "-", text)
    return text.strip("-") or "article"


def _extract_links_the_ringer(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "theringer.com" in href or href.startswith("/"):
            url = urljoin(base_url, href)
            if "/nba" in url and "/tag/" not in url and "/category/" not in url:
                links.append(url)
    return links


def _extract_links_action_network(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        url = urljoin(base_url, href)
        if "actionnetwork.com" in url and "/nba/" in url and all(x not in url for x in ["/odds", "/picks", "/glossary", "/education", "/betting-terms"]):
            links.append(url)
    return links


def _extract_links_clutchpoints(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        url = urljoin(base_url, href)
        if "clutchpoints.com" in url and "/nba/" in url and "/tag/" not in url:
            links.append(url)
    return links


def _extract_links_nba(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        url = urljoin(base_url, href)
        if "nba.com/news" in url and any(ch.isalpha() for ch in url.split("/")[-1]):
            links.append(url)
    return links


def extract_article_links(source_name: str, html: str, base_url: str) -> List[str]:
    if source_name == "the_ringer":
        links = _extract_links_the_ringer(html, base_url)
    elif source_name == "action_network":
        links = _extract_links_action_network(html, base_url)
    elif source_name == "clutchpoints":
        links = _extract_links_clutchpoints(html, base_url)
    elif source_name == "nba_com":
        links = _extract_links_nba(html, base_url)
    else:
        links = []
    # Normalize and dedupe by path
    seen = set()
    normalized = []
    for url in links:
        try:
            p = urlparse(url)
        except Exception:
            continue
        key = f"{p.scheme}://{p.netloc}{p.path}"
        if key not in seen:
            seen.add(key)
            normalized.append(key)
    return normalized


async def scrape_and_save(source_name: str, force: bool, save_html: bool, collect_articles: bool, max_articles: int):
    """Scrapes a source listing page; reuses cached HTML; optionally saves HTML and collects full articles."""
    if source_name not in SCRAPE_SOURCES:
        raise ValueError(f"Unknown source: {source_name}")

    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    html_path = os.path.join(output_dir, f"{source_name}.html")
    md_path = os.path.join(output_dir, f"{source_name}.md")

    listing_html = None
    # If cached HTML exists and not forcing, reuse it for markdown and possibly article collection
    if os.path.exists(html_path) and not force:
        with open(html_path, "r", encoding="utf-8") as f:
            listing_html = f.read()
        print(f"✅ Reused cached HTML for {source_name}")

    url = SCRAPE_SOURCES[source_name]
    print(f"🔍 Scraping with Playwright: {source_name} ({url})")

    # If we don't have listing_html yet, fetch it now
    if listing_html is None:
        async with async_playwright() as p:
            if source_name in {"action_network", "the_ringer", "clutchpoints", "nba_com"}:
                browser = await p.firefox.launch(headless=True)
            else:
                browser = await p.chromium.launch(headless=True)
            scraper = ScrapingService(browser)
            # Site-specific navigation tuning
            if source_name in {"clutchpoints", "nba_com"}:
                listing_html = await scraper.scrape_page(
                    url,
                    wait_until="domcontentloaded",
                    timeout_ms=120000,
                    retries=2,
                    scroll_passes=4,
                )
            else:
                listing_html = await scraper.scrape_page(
                    url,
                    wait_until="networkidle",
                    timeout_ms=90000,
                    retries=2,
                    scroll_passes=3,
                )
            if not listing_html:
                print(f"❌ Playwright scrape failed for {source_name}. No HTML content found.")
                return
            if save_html:
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(listing_html)
                print(f"📄 Saved raw HTML to: {html_path}")

    # Convert listing HTML to Markdown
    h = html2text.HTML2Text()
    h.ignore_links = False
    markdown = h.handle(listing_html)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"✅ Listing processed for {source_name}")
    print(f"📄 Saved scraped markdown to: {md_path}")
    print("📄 Preview:\n", markdown[:500])

    # Optionally collect and save full articles
    if collect_articles:
        article_links = extract_article_links(source_name, listing_html, url)
        if not article_links:
            print(f"ℹ️ No article links found for {source_name}")
            return
        max_count = max(1, int(max_articles))
        target_links = article_links[:max_count]
        articles_dir = os.path.join(output_dir, source_name, "articles")
        os.makedirs(articles_dir, exist_ok=True)

        async with async_playwright() as p:
            if source_name in {"action_network", "the_ringer", "clutchpoints", "nba_com"}:
                browser = await p.firefox.launch(headless=True)
            else:
                browser = await p.chromium.launch(headless=True)
            scraper = ScrapingService(browser)

            saved = 0
            for link in target_links:
                slug = _slugify(urlparse(link).path.rsplit("/", 1)[-1])
                art_html_path = os.path.join(articles_dir, f"{slug}.html")
                art_md_path = os.path.join(articles_dir, f"{slug}.md")
                if os.path.exists(art_html_path) and not force:
                    print(f"↪️  Skipping existing article (cached): {slug}")
                    saved += 1
                    continue
                # Article-level tuning per site
                if source_name in {"clutchpoints", "nba_com"}:
                    html = await scraper.scrape_page(
                        link,
                        wait_until="domcontentloaded",
                        timeout_ms=120000,
                        retries=2,
                        scroll_passes=5,
                    )
                else:
                    html = await scraper.scrape_page(
                        link,
                        wait_until="networkidle",
                        timeout_ms=90000,
                        retries=2,
                        scroll_passes=3,
                    )
                if not html:
                    print(f"❌ Failed to fetch article: {link}")
                    continue
                with open(art_html_path, "w", encoding="utf-8") as f:
                    f.write(html)
                h2 = html2text.HTML2Text()
                h2.ignore_links = False
                md = h2.handle(html)
                with open(art_md_path, "w", encoding="utf-8") as f:
                    f.write(md)
                print(f"✅ Saved article: {slug}")
                saved += 1
            print(f"📦 Saved {saved} article(s) for {source_name} at {articles_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape NBA content using Playwright")
    parser.add_argument(
        "--source",
        choices=list(SCRAPE_SOURCES.keys()),
        required=True,
        help="Source to scrape (e.g., nba_com, the_ringer)"
    )
    parser.add_argument(
        "--force-scrape",
        action="store_true",
        help="Ignore cached HTML and force a fresh scrape",
    )
    parser.add_argument(
        "--save-html",
        action="store_true",
        help="Save the raw HTML to data/{source}.html for this run",
    )
    parser.add_argument(
        "--collect-articles",
        action="store_true",
        help="Extract article links from the listing page and save full articles",
    )
    parser.add_argument(
        "--max-articles",
        type=int,
        default=5,
        help="Maximum number of articles to collect per source",
    )
    args = parser.parse_args()
    asyncio.run(
        scrape_and_save(
            args.source,
            force=args.force_scrape,
            save_html=args.save_html,
            collect_articles=args.collect_articles,
            max_articles=args.max_articles,
        )
    )
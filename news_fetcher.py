import feedparser
import requests
from bs4 import BeautifulSoup

def get_pib_news():

    rss_url = (
        "https://news.google.com/rss/search?"
        "q=site:pib.gov.in"
    )

    feed = feedparser.parse(rss_url)

    news = []

    for item in feed.entries[:10]:

        news.append({
            "title": item.title,
            "link": item.link
        })

    return news


def extract_article_text(url):

    try:

        headers = {
            "User-Agent":"Mozilla/5.0"
        }

        r = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        soup = BeautifulSoup(
            r.text,
            "html.parser"
        )

        paragraphs = soup.find_all("p")

        article = ""

        for p in paragraphs:

            article += p.get_text(" ")

            article += "\n"

        return article[:5000]

    except Exception:

        return ""

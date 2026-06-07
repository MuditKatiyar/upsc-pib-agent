import os
import requests
import feedparser
from bs4 import BeautifulSoup
from google import genai
from datetime import datetime
import pytz

# =========================
# CONFIG
# =========================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# =========================
# TIME
# =========================

def get_indian_time():
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist)

# =========================
# TELEGRAM
# =========================

def send_telegram(text):

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }

    try:
        r = requests.post(url, json=payload, timeout=30)

        print("Telegram Status:", r.status_code)
        print("Telegram Response:", r.text)

    except Exception as e:
        print("Telegram Error:", e)

# =========================
# PIB RSS
# =========================

def fetch_pib_news():

    rss_url = "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3"

    print("Checking RSS:", rss_url)

    feed = feedparser.parse(rss_url)

    print("RSS Entries Found:", len(feed.entries))

    articles = []

    for item in feed.entries:

        articles.append({
            "title": item.title,
            "link": item.link
        })

    return articles

# =========================
# PRS
# =========================

def fetch_prs_data():

    url = "https://prsindia.org/policy/monthly-policy-review"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        print("PRS Status:", response.status_code)
        print("PRS Page Length:", len(response.text))

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        links = soup.find_all("a", href=True)

        data = []

        for link in links:

            href = link["href"]
            title = link.get_text(strip=True)

            if title and len(title) > 5:

                if (
                    "monthly-policy-review" in href
                    or "/files/" in href
                ):

                    full_url = (
                        href
                        if href.startswith("http")
                        else f"https://prsindia.org{href}"
                    )

                    data.append({
                        "title": title,
                        "link": full_url
                    })

        print("PRS Items Found:", len(data))

        return data[:5]

    except Exception as e:

        print("PRS Error:", e)

        return []

# =========================
# GEMINI
# =========================

def generate_report(pib_news, prs_news):

    raw = ""

    raw += "PIB NEWS\n\n"

    for x in pib_news:

        raw += (
            f"Title: {x['title']}\n"
            f"Link: {x['link']}\n\n"
        )

    raw += "\nPRS NEWS\n\n"

    for x in prs_news:

        raw += (
            f"Title: {x['title']}\n"
            f"Link: {x['link']}\n\n"
        )

    prompt = f"""
Create UPSC current affairs notes.

For every PIB article:
- Heading
- 2 line summary
- UPSC relevance

For every PRS review:
- Title
- Explanation
- UPSC relevance

Data:

{raw}
"""

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text

# =========================
# MAIN
# =========================

if __name__ == "__main__":

    print("=" * 50)
    print("UPSC AGENT STARTED")
    print("=" * 50)

    print("Gemini Key:", bool(GEMINI_API_KEY))
    print("Telegram Token:", bool(TELEGRAM_BOT_TOKEN))
    print("Telegram Chat:", bool(TELEGRAM_CHAT_ID))

    pib_news = fetch_pib_news()
    prs_news = fetch_prs_data()

    print("=" * 50)
    print("PIB COUNT:", len(pib_news))
    print("PRS COUNT:", len(prs_news))
    print("=" * 50)

    if len(pib_news) > 0:
        print("FIRST PIB ARTICLE")
        print(pib_news[0])

    if len(prs_news) > 0:
        print("FIRST PRS ARTICLE")
        print(prs_news[0])

    # Debug Telegram
    send_telegram(
        f"DEBUG\nPIB={len(pib_news)}\nPRS={len(prs_news)}"
    )

    if len(pib_news) == 0 and len(prs_news) == 0:

        send_telegram(
            "No new updates found on PIB or PRS today."
        )

        raise Exception(
            "Both PIB and PRS returned zero results."
        )

    report = generate_report(
        pib_news,
        prs_news
    )

    send_telegram(report)

    print("DONE")

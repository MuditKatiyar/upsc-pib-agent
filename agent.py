import os
import requests
import feedparser
from bs4 import BeautifulSoup
from google import genai
from datetime import datetime
import pytz

# ==============================
# ENV VARIABLES
# ==============================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ==============================
# IST TIME
# ==============================

def get_indian_time():
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist)

# ==============================
# PIB RSS
# ==============================

def fetch_pib_news():

    rss_url = "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3"

    feed = feedparser.parse(rss_url)

    articles = []

    for entry in feed.entries[:20]:

        articles.append(
            {
                "title": entry.title,
                "link": entry.link
            }
        )

    print(f"PIB Articles Found: {len(articles)}")

    return articles

# ==============================
# PRS POLICY REVIEWS
# ==============================

def fetch_prs_data():

    print("Fetching PRS data...")

    url = "https://prsindia.org/policy/monthly-policy-review"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    reviews = []

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        print("PRS Status:", response.status_code)

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        links = soup.find_all(
            "a",
            href=True
        )

        for link in links:

            text = link.get_text(strip=True)

            href = link["href"]

            if (
                "monthly-policy-review" in href
                or "/files/" in href
            ):

                full_url = (
                    href
                    if href.startswith("http")
                    else f"https://prsindia.org{href}"
                )

                reviews.append(
                    {
                        "title": text if text else "PRS Policy Review",
                        "link": full_url
                    }
                )

        unique = []

        seen = set()

        for item in reviews:

            if item["link"] not in seen:

                seen.add(item["link"])

                unique.append(item)

        print(f"PRS Reviews Found: {len(unique)}")

        return unique[:5]

    except Exception as e:

        print("PRS Error:", e)

        return []

# ==============================
# GEMINI ANALYSIS
# ==============================

def generate_upsc_notes(
        date_str,
        pib_news,
        prs_reviews
):

    raw_text = ""

    raw_text += "===== PIB NEWS =====\n"

    for i, article in enumerate(
            pib_news,
            start=1
    ):

        raw_text += (
            f"{i}. "
            f"{article['title']}\n"
            f"Link: {article['link']}\n\n"
        )

    raw_text += "\n===== PRS REVIEWS =====\n"

    for i, article in enumerate(
            prs_reviews,
            start=1
    ):

        raw_text += (
            f"{i}. "
            f"{article['title']}\n"
            f"Link: {article['link']}\n\n"
        )

    prompt = f"""
You are a UPSC Current Affairs Analyst.

Date: {date_str}

Create a structured UPSC current affairs note.

Format:

🔴 TODAY'S PIB CURRENT AFFAIRS

For each PIB item:
- Heading
- 2 line summary
- Why important for UPSC

🟣 PRS MONTHLY POLICY REVIEW

For each PRS item:
- Title
- Brief explanation
- UPSC relevance

Raw Data:

{raw_text}
"""

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text

# ==============================
# TELEGRAM
# ==============================

def send_to_telegram(message):

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}"
        f"/sendMessage"
    )

    chunks = [
        message[i:i+3900]
        for i in range(
            0,
            len(message),
            3900
        )
    ]

    for chunk in chunks:

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk
        }

        try:

            r = requests.post(
                url,
                json=payload,
                timeout=20
            )

            print(
                "Telegram:",
                r.status_code
            )

            print(r.text)

        except Exception as e:

            print(
                "Telegram Error:",
                e
            )

# ==============================
# MAIN
# ==============================

if __name__ == "__main__":

    print("===== STARTING UPSC AGENT =====")

    print(
        "Gemini Key Present:",
        bool(GEMINI_API_KEY)
    )

    print(
        "Telegram Token Present:",
        bool(TELEGRAM_BOT_TOKEN)
    )

    print(
        "Chat ID Present:",
        bool(TELEGRAM_CHAT_ID)
    )

    today = get_indian_time()

    date_str = today.strftime(
        "%d-%m-%Y"
    )

    pib_news = fetch_pib_news()

    prs_reviews = fetch_prs_data()

    if len(pib_news) == 0:

        send_to_telegram(
            "⚠️ No PIB news fetched."
        )

        raise Exception(
            "PIB returned zero articles."
        )

    print(
        "Generating UPSC Notes..."
    )

    report = generate_upsc_notes(
        date_str,
        pib_news,
        prs_reviews
    )

    print(
        "Sending to Telegram..."
    )

    send_to_telegram(report)

    print(
        "===== COMPLETED SUCCESSFULLY ====="
    )

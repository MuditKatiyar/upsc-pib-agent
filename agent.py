import os
import feedparser
import requests
from google import genai

# Fetch variables from GitHub Secrets
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

FEEDS = {
    "PIB_Delhi": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=1",
    "PRS_Blog": "https://prsindia.org/articles-by-prs-team/feed" 
}

def fetch_daily_news():
    extracted_articles = []
    for source, url in FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]: # Top 5 items
            extracted_articles.append({
                "source": source,
                "title": entry.title,
                "link": entry.link,
                "summary": entry.get("summary", entry.title)
            })
    return extracted_articles

def analyze_with_ai(articles):
    if not articles:
        return "No new updates found on PIB or PRS today."
    
    raw_data = ""
    for idx, art in enumerate(articles, 1):
        raw_data += f"\n[{idx}] Source: {art['source']}\nTitle: {art['title']}\nLink: {art['link']}\nSummary: {art['summary']}\n---"

    upsc_prompt = f"""
    You are an expert civil services coach specializing in UPSC preparation. 
    Analyze the following official raw press releases/articles from PIB and PRS. 
    Filter out routine administrative updates. Only select items relevant to GS Paper I, II, and III.
    
    For each highly relevant news item, provide an analysis in this exact format:
    1. 📰 **Heading**: Clear crisp title.
    2. 📝 **Context & Syllabus Correlation**: Which GS Paper (I/II/III) and specific topic it maps to.
    3. 🧠 **Logical Explanation**: Explain the core concept/scheme/bill in simple terms. 
    4. 🔍 **Key Facts for Prelims**: Crucial factual points (Committees, dates, nodal ministries, indices).
    5. ✍️ **Mains Perspective**: Why is this important for Mains? (2 Pros, 2 Cons, or critical impact).
    
    Raw Data:
    {raw_data}
    """
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=upsc_prompt
    )
    return response.text

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    news = fetch_daily_news()
    analysis = analyze_with_ai(news)
    send_to_telegram(analysis)

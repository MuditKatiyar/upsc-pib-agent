import os
import requests
from bs4 import BeautifulSoup
from google import genai

# Fetch variables from GitHub Secrets
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 📅 BACKDATING CONFIGURATION: 
# To fetch today's current news, leave this as "".
# To fetch an old date, type it in "DD-MM-YYYY" format. Example: "15-08-2025"
TARGET_DATE = "" 

def get_date_parameters():
    if TARGET_DATE:
        day, month, year = TARGET_DATE.split("-")
        return int(day), int(month), int(year)
    else:
        # Dynamically calculate today's date in Indian Standard Time (IST)
        from datetime import datetime
        import pytz
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        return now.day, now.month, now.year

def fetch_pib_archive_news():
    day, month, year = get_date_parameters()
    print(f"Targeting PIB Archive Date: {day:02d}-{month:02d}-{year}")
    
    # Official PIB regional portal link format for specific calendar dates
    archive_url = f"https://pib.gov.in/AllRelease.aspx?Day={day}&Month={month}&Year={year}&Reg=3&Lang=1"
    
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    response = requests.get(archive_url, headers=headers)
    
    extracted_articles = []
    if response.status_code != 200:
        return extracted_articles

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Locate press release anchors inside the official archival document list
    links = soup.find_all('a', href=True)
    count = 0
    
    for link in links:
        if "PressReleasePage.aspx" in link['href']:
            title = link.text.strip()
            full_url = f"https://pib.gov.in/{link['href']}"
            if title and full_url not in [a['link'] for a in extracted_articles]:
                extracted_articles.append({
                    "source": "PIB Archive",
                    "title": title,
                    "link": full_url,
                    "summary": title
                })
                count += 1
                if count >= 8:  # Limit to top 8 major releases to avoid hitting LLM token ceilings
                    break
                    
    return extracted_articles

def analyze_with_ai(articles):
    day, month, year = get_date_parameters()
    date_str = f"{day:02d}-{month:02d}-{year}"
    
    if not articles:
        return f"No official press releases found in the PIB archives for the date: {date_str}."
    
    raw_data = ""
    for idx, art in enumerate(articles, 1):
        raw_data += f"\n[{idx}] Title: {art['title']}\nLink: {art['link']}\n---"

    upsc_prompt = f"""
    You are an expert civil services coach specializing in UPSC preparation. 
    Analyze the following official raw press releases from PIB for the historic date: {date_str}. 
    Filter out routine administrative announcements or local event updates. Only select items relevant to GS Paper I, II, and III.
    
    For each highly relevant news item, provide a comprehensive analysis in this exact format:
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
    news = fetch_pib_archive_news()
    print(f"Extracted {len(news)} items. Submitting to Gemini engine...")
    analysis = analyze_with_ai(news)
    send_to_telegram(analysis)
    print("Historical package delivered successfully!")

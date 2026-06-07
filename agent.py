import os
import requests
from bs4 import BeautifulSoup
from google import genai
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytz

# Fetch variables from GitHub Secrets
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def get_indian_time():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)

def fetch_pib_news_for_date(date_obj):
    day = date_obj.day
    month = date_obj.month
    year = date_obj.year
    date_str = date_obj.strftime("%d-%m-%Y")
    
    print(f"Fetching archive data for: {date_str}")
    archive_url = f"https://pib.gov.in/AllRelease.aspx?Day={day}&Month={month}&Year={year}&Reg=3&Lang=1"
    
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    extracted_articles = []
    
    try:
        response = requests.get(archive_url, headers=headers, timeout=15)
        if response.status_code != 200:
            return extracted_articles
            
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        count = 0
        
        for link in links:
            if "PressReleasePage.aspx" in link['href']:
                title = link.text.strip()
                full_url = f"https://pib.gov.in/{link['href']}"
                if title and full_url not in [a['link'] for a in extracted_articles]:
                    extracted_articles.append({
                        "title": title,
                        "link": full_url
                    })
                    count += 1
                    if count >= 6:  # Limit per day to keep context window precise
                        break
    except Exception as e:
        print(f"Error fetching data for {date_str}: {e}")
        
    return extracted_articles

def format_raw_data(title_header, articles):
    if not articles:
        return f"\n### {title_header}\nNo significant press releases found for this date.\n"
    
    output = f"\n### {title_header}\n"
    for idx, art in enumerate(articles, 1):
        output += f"[{idx}] Title: {art['title']}\nLink: {art['link']}\n---\n"
    return output

def run_analytical_engine(current_date_str, past_date_str, consolidated_data):
    upsc_prompt = f"""
    You are an expert civil services mentor specializing in UPSC CSE preparation.
    Analyze the following official raw text datasets compiled from the Press Information Bureau (PIB).
    
    The dataset contains two parts:
    1. Current Day Updates ({current_date_str})
    2. Historical Revision Updates ({past_date_str})
    
    Filter out routine administrative announcements or local event updates. Only select items highly relevant to GS Paper I, II, and III.
    
    Present your final output clearly split into TWO main parts:
    
    =========================================
    🔴 PART A: TODAY'S CURRENT AFFAIRS ({current_date_str})
    =========================================
    For each selected item, provide:
    - 📰 **Heading**: Clear, crisp title.
    - 📝 **Syllabus Corelation**: GS Paper (I/II/III) and specific micro-topic.
    - 🧠 **Logical Concept**: Explanation of the core scheme/bill/concept in very simple terms.
    - 🔍 **Prelims Pointers**: Nodal ministries, dates, targets, important indices or numbers.
    - ✍️ **Mains Perspective**: Brief structural analysis (2 Pros, 2 Cons, or strategic impacts).
    
    =========================================
    🔵 PART B: PREVIOUS MONTH BACKFILL REVISION ({past_date_str})
    =========================================
    Apply the exact same structured layout for the historical items so they can be archived directly into study notes.
    
    Raw Source Materials:
    {consolidated_data}
    """
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=upsc_prompt
    )
    return response.text

def send_telegram_chunks(text):
    # Telegram character limit safety check (4096 max per message block)
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    if len(text) <= 4000:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})
    else:
        # Split cleanly across headings if the output is extremely descriptive
        parts = text.split("=========================================")
        for part in parts:
            if part.strip():
                formatted_part = "=========================================\n" + part
                requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": formatted_part, "parse_mode": "Markdown"})

if __name__ == "__main__":
    # Calculate dates dynamically
    today_ist = get_indian_time()
    previous_month_ist = today_ist - relativedelta(months=1)
    
    today_str = today_ist.strftime("%d-%m-%Y")
    past_str = previous_month_ist.strftime("%d-%m-%Y")
    
    print(f"Processing Day Cycle: Today ({today_str}) & Previous Month Backfill ({past_str})")
    
    # Run fetchers
    current_news = fetch_pib_news_for_date(today_ist)
    past_news = fetch_pib_news_for_date(previous_month_ist)
    
    # Consolidate raw text logs
    compiled_raw_material = format_raw_data(f"Current Releases ({today_str})", current_news)
    compiled_raw_material += format_raw_data(f"Historical Archive Releases ({past_str})", past_news)
    
    # AI Processing and delivery
    print("Initiating analytical summary sequence...")
    final_digest = run_analytical_engine(today_str, past_str, compiled_raw_material)
    
    print("Transmitting content blocks to Telegram channel...")
    send_telegram_chunks(final_digest)
    print("All tasks executed successfully!")

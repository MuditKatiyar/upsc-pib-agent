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
    
    print(f"Scraping ALL PIB entries for: {date_str}")
    archive_url = f"https://pib.gov.in/AllRelease.aspx?Day={day}&Month={month}&Year={year}&Reg=3&Lang=1"
    
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    extracted_articles = []
    
    try:
        response = requests.get(archive_url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            for link in links:
                if "PressReleasePage.aspx" in link['href']:
                    title = link.text.strip()
                    full_url = f"https://pib.gov.in/{link['href']}"
                    if title and full_url not in [a['link'] for a in extracted_articles]:
                        extracted_articles.append({
                            "title": title,
                            "link": full_url
                        })
    except Exception as e:
        print(f"Error scraping PIB for {date_str}: {e}")
        
    return extracted_articles

def fetch_prs_data():
    print("Scraping targeted targets from PRS India...")
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    prs_items = []
    
    # Target 1: Parliament Today Tracking Dashboard
    try:
        parl_url = "https://prsindia.org/"
        resp = requests.get(parl_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            announcements = soup.find_all('a', href=True)
            for link in announcements:
                text = link.text.strip()
                href = link['href']
                if any(keyword in text.lower() for keyword in ["draft", "bill", "code", "amendment", "rules", "act"]):
                    full_url = href if href.startswith("http") else f"https://prsindia.org{href}"
                    if text and full_url not in [p['link'] for p in prs_items]:
                        prs_items.append({"title": f"Parliament Section: {text}", "link": full_url})
    except Exception as e:
        print(f"Error parsing PRS Parliament: {e}")

    # Target 2: Monthly Policy Review Archives
    try:
        policy_url = "https://prsindia.org/policy/monthly-policy-review"
        resp = requests.get(policy_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            policy_links = soup.find_all('a', href=True)
            count = 0
            for link in policy_links:
                text = link.text.strip()
                href = link['href']
                if "monthly-policy-review" in href and any(m in text for m in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]):
                    full_url = href if href.startswith("http") else f"https://prsindia.org{href}"
                    if full_url not in [p['link'] for p in prs_items]:
                        prs_items.append({"title": f"Monthly Policy Review: {text}", "link": full_url})
                        count += 1
                        if count >= 3:  # Grabs the top 3 latest monthly documents
                            break
    except Exception as e:
        print(f"Error parsing PRS Monthly Policy: {e}")
        
    return prs_items

def run_analytical_engine(current_date_str, past_date_str, pib_current, pib_past, prs_data):
    # Compile everything cleanly into text layout
    raw_material = f"=== [PART 1] LIVE DAILY PIB RELEASES ({current_date_str}) ===\n"
    if not pib_current:
        raw_material += "No raw releases found on the portal for this date.\n"
    for i, a in enumerate(pib_current, 1):
        raw_material += f"[{i}] {a['title']} - Link: {a['link']}\n"
        
    raw_material += f"\n=== [PART 2] HISTORICAL MONTHLY PIB BACKFILL ({past_date_str}) ===\n"
    if not pib_past:
        raw_material += "No raw releases found on the portal for this date.\n"
    for i, a in enumerate(pib_past, 1):
        raw_material += f"[{i}] {a['title']} - Link: {a['link']}\n"
        
    raw_material += f"\n=== [PART 3] TARGETED PRS LEGISLATIVE DOSSIERS ===\n"
    if not prs_data:
        raw_material += "No active legislative updates found on the portal dashboard.\n"
    for i, a in enumerate(prs_data, 1):
        raw_material += f"[{i}] {a['title']} - Link: {a['link']}\n"

    upsc_prompt = f"""
    You are an AI assistant formatting official government data streams. 
    Do not skip, filter out, or omit any news items from the lists provided below. Process all of them.
    
    Organize the output into these three sections using clean Markdown formatting:
    
    =========================================
    🔴 SECTION 1: TODAY'S CURRENT AFFAIRS ({current_date_str})
    =========================================
    List every single item found in Part 1. For each item, output:
    - 📰 **Heading**: The title of the release.
    - 🔗 **Source Link**: The official URL.
    - 📝 **Brief Summary**: A simple 2-3 sentence overview explaining what this notification is about.
    
    =========================================
    🔵 SECTION 2: PREVIOUS MONTH REVISION BACKFILL ({past_date_str})
    =========================================
    List every single item found in Part 2 using the exact same style (Heading, Source Link, and Brief Summary).
    
    =========================================
    🟣 SECTION 3: PRS LEGISLATIVE & POLICY BRIEFING
    =========================================
    List the items from Part 3 with their respective links and a short summary of the policy document or draft bill.
    
    Raw Data Content:
    {raw_material}
    """
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=upsc_prompt
    )
    return response.text

def send_telegram_chunks(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    if len(text) <= 4000:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})
    else:
        parts = text.split("=========================================")
        for part in parts:
            if part.strip():
                formatted_part = "=========================================\n" + part
                if len(formatted_part) > 4000:
                    # Fallback split for massive lists of releases
                    sub_parts = [formatted_part[i:i+4000] for i in range(0, len(formatted_part), 4000)]
                    for sp in sub_parts:
                        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": sp, "parse_mode": "Markdown"})
                else:
                    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": formatted_part, "parse_mode": "Markdown"})

if __name__ == "__main__":
    today_ist = get_indian_time()
    previous_month_ist = today_ist - relativedelta(months=1)
    
    today_str = today_ist.strftime("%d-%m-%Y")
    past_str = previous_month_ist.strftime("%d-%m-%Y")
    
    pib_current_data = fetch_pib_news_for_date(today_ist)
    pib_past_data = fetch_pib_news_for_date(previous_month_ist)
    prs_filtered_data = fetch_prs_data()
    
    print("Processing all items into the formatting engine...")
    final_analysis = run_analytical_engine(today_str, past_str, pib_current_data, pib_past_data, prs_filtered_data)
    
    print("Transmitting raw formatted data stream to Telegram...")
    send_telegram_chunks(final_analysis)
    print("Pipeline run successfully completed!")

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
    # Forces the cloud container to always use Indian Standard Time calendar rules
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist)

def fetch_pib_news_for_date(date_obj):
    day = date_obj.day
    month = date_obj.month
    year = date_obj.year
    date_str = date_obj.strftime("%d-%m-%Y")
    
    print(f"Scraping ALL PIB entries for India Date: {date_str}")
    # Constructing the exact query matching the live browser filters
    archive_url = f"https://pib.gov.in/AllRelease.aspx?Day={day}&Month={month}&Year={year}&Reg=3&Lang=1"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    extracted_articles = []
    
    try:
        response = requests.get(archive_url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Target the specific container div that holds the press release links on the live site
            content_div = soup.find('div', class_='content-area')
            search_pool = content_div.find_all('a', href=True) if content_div else soup.find_all('a', href=True)
            
            for link in search_pool:
                href = link['href']
                if "PressReleasePage.aspx" in href or "Pressreleaseshare.aspx" in href:
                    title = link.text.strip()
                    # Reconstruct complete absolute path cleanly
                    if href.startswith("AllRelease.aspx") or href.startswith("PressReleasePage.aspx") or href.startswith("Pressreleaseshare.aspx"):
                        full_url = f"https://pib.gov.in/{href}"
                    else:
                        full_url = href if href.startswith("http") else f"https://pib.gov.in{href}"
                        
                    if title and len(title) > 5 and full_url not in [a['link'] for a in extracted_articles]:
                        extracted_articles.append({
                            "title": title,
                            "link": full_url
                        })
    except Exception as e:
        print(f"Error scraping PIB for {date_str}: {e}")
        
    return extracted_articles

def fetch_prs_data():
    print("Scraping targeted sectors from PRS India...")
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    prs_items = []
    
    # 🎯 Target 1: Parliament Today Dashboard
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

    # 🎯 Target 2: Deep-Scraping Monthly Policy Review Archives
    try:
        policy_url = "https://prsindia.org/policy/monthly-policy-review"
        resp = requests.get(policy_url, headers=headers, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            all_links = soup.find_all('a', href=True)
            
            count = 0
            for link in all_links:
                href = link['href']
                text = link.text.strip()
                
                if "monthly-policy-review" in href or "Monthly" in href:
                    full_url = href if href.startswith("http") else f"https://prsindia.org{href}"
                    display_title = text if text else f"Monthly Policy Review Dossier"
                    if len(display_title) > 10 and full_url not in [p['link'] for p in prs_items]:
                        prs_items.append({"title": f"Monthly Policy Review: {display_title}", "link": full_url})
                        count += 1
                        if count >= 3: 
                            break
    except Exception as e:
        print(f"Error parsing PRS Monthly Policy: {e}")
        
    return prs_items

def run_analytical_engine(current_date_str, past_date_str, pib_current, pib_past, prs_data):
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
    List every single item found in Part 3. Provide the title, their respective links, and a brief description summarizing the policy document or draft bill.
    
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

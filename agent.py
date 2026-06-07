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
    
    print(f"Scraping PIB Archive for Date: {date_str}")
    # Using the exact URL query structure for the live main archive page
    archive_url = f"https://pib.gov.in/indexDirect.aspx?Regid=3&Lid=1"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    extracted_articles = []
    
    try:
        response = requests.get(archive_url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link['href']
                title = link.text.strip()
                if "PressReleasePage.aspx" in href or "ReleaseId=" in href:
                    if title and len(title) > 10:
                        full_url = href if href.startswith("http") else f"https://pib.gov.in/{href.lstrip('/')}"
                        if full_url not in [a['link'] for a in extracted_articles]:
                            extracted_articles.append({
                                "title": title,
                                "link": full_url
                            })
    except Exception as e:
        print(f"Error reading PIB: {e}")
        
    return extracted_articles

def fetch_prs_data():
    print("Scraping direct elements from PRS Policy Archive...")
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    prs_items = []
    
    try:
        # Hitting the main monthly policy review archive node directly
        url = "https://prsindia.org/policy/monthly-policy-review"
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link['href']
                text = link.text.strip()
                
                if "monthly-policy-review" in href or "/files/policy/" in href:
                    if "Review" in text or any(m in text for m in ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]):
                        full_url = href if href.startswith("http") else f"https://prsindia.org{href}"
                        if full_url not in [p['link'] for p in prs_items]:
                            prs_items.append({
                                "title": text if text else "Monthly Policy Review",
                                "link": full_url
                            })
    except Exception as e:
        print(f"Error reading PRS: {e}")
        
    return prs_items[:5]  # Returns the top 5 most recent monthly review files found

def run_analytical_engine(current_date_str, past_date_str, pib_current, pib_past, prs_data):
    raw_material = f"=== PART 1: DAILY PIB RELEASES FOR TODAY ({current_date_str}) ===\n"
    for i, a in enumerate(pib_current, 1):
        raw_material += f"[{i}] Title: {a['title']} | Link: {a['link']}\n"
        
    raw_material += f"\n=== PART 2: PREVIOUS MONTH PIB BACKFILL ({past_date_str}) ===\n"
    for i, a in enumerate(pib_past, 1):
        raw_material += f"[{i}] Title: {a['title']} | Link: {a['link']}\n"
        
    raw_material += f"\n=== PART 3: PRS MONTHLY POLICY REVIEWS ===\n"
    for i, a in enumerate(prs_data, 1):
        raw_material += f"[{i}] Title: {a['title']} | Link: {a['link']}\n"

    upsc_prompt = f"""
    You are an un-filtered administrative data formatting engine. 
    Do not pick, choose, skip, or filter any items. Process every single item present in the raw data text.
    
    Format the complete output using clean Markdown headers:
    
    =========================================
    🔴 SECTION 1: TODAY'S CURRENT AFFAIRS ({current_date_str})
    =========================================
    List every single item found in Part 1. For each item:
    - 📰 **Heading**: Exact title text.
    - 🔗 **Link**: URL link.
    - 📝 **Summary**: A short 2-sentence description of the release.
    
    =========================================
    🔵 SECTION 2: PREVIOUS MONTH REVISION ({past_date_str})
    =========================================
    List every single item found in Part 2 formatted exactly like Section 1.
    
    =========================================
    🟣 SECTION 3: PRS MONTHLY POLICY HIGHLIGHTS
    =========================================
    List every single item found in Part 3. Provide the full title, direct download link, and a brief overview of what this monthly policy docket updates.
    
    Raw Source Pool:
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
    
    print("Formatting entire collected data matrix...")
    final_analysis = run_analytical_engine(today_str, past_str, pib_current_data, pib_past_data, prs_filtered_data)
    
    print("Transmitting package to Telegram...")
    send_telegram_chunks(final_analysis)
    print("Execution Finished Successfully!")

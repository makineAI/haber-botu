import os
import requests
from bs4 import BeautifulSoup
from pyairtable import Api
from dotenv import load_dotenv

load_dotenv()

# --- AYARLAR ---
AIRTABLE_API_KEY = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = "appC4JNkqLfVCEcna"
AIRTABLE_TABLE_ID = "tbl1paeNlwYfvKQlP"

api = Api(AIRTABLE_API_KEY)
table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_ID)

def get_existing_data():
    try:
        records = table.all()
        urls = [r['fields'].get('url') for r in records if 'url' in r['fields']]
        titles = [r['fields'].get('haber_basliği', '').lower().strip() for r in records]
        return urls, titles
    except Exception as e:
        print(f"Airtable hatası: {e}")
        return [], []

def scrape_data():
    existing_urls, existing_titles = get_existing_data()
    print(f"Tarama Başladı... Mevcut Kayıt: {len(existing_titles)}")

    # --- 1. FORUM MAKİNA (Sayfalı) ---
    print("\n[1/3] Forum Makina taranıyor...")
    page = 1
    continue_scraping = True
    while continue_scraping:
        print(f"Sayfa {page} kontrol ediliyor...")
        url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        try:
            r = requests.get(url, timeout=20)
            soup = BeautifulSoup(r.content, "html.parser")
            items = soup.find_all("div", class_="title")
            
            if not items: break # Sayfa boşsa dur
            
            found_2026_in_page = False
            for item in items:
                parent = item.find_parent()
                tarih = parent.find("div", class_="date").text if parent.find("div", class_="date") else ""
                
                if "2026" in tarih:
                    found_2026_in_page = True
                    baslik = item.text.strip()
                    link = "https://www.forummakina.com.tr" + parent.find("a")["href"]
                    if link not in existing_urls and baslik.lower().strip() not in existing_titles:
                        table.create({
                            "haber_basliği": baslik,
                            "gorsel": parent.find("img")["src"] if parent.find("img") else "",
                            "haber_metni": parent.find("span").text.replace("devamı", "").strip() if parent.find("span") else "",
                            "portal": "Forum Makina",
                            "url": link
                        })
                        print(f"Eklendi: {baslik}")
                
            if not found_2026_in_page: continue_scraping = False # Bu sayfada hiç 2026 yoksa diğer sayfalara bakma
            page += 1
        except: break

    # --- 2. LHT (Sayfalı) ---
    print("\n[2/3] LHT taranıyor...")
    page = 1
    continue_scraping = True
    while continue_scraping:
        url = f"https://www.lht.com.tr/kategori/haber/page/{page}/"
        print(f"Sayfa {page} kontrol ediliyor...")
        try:
            r = requests.get(url, timeout=20)
            if r.status_code != 200: break
            soup = BeautifulSoup

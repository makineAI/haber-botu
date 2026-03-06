import os
import requests
from bs4 import BeautifulSoup
from pyairtable import Api
from dotenv import load_dotenv

# .env dosyasındaki değişkenleri yükle
load_dotenv()

# --- AYARLAR ---
AIRTABLE_API_KEY = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = "appC4JNkqLfVCEcna"
AIRTABLE_TABLE_ID = "tbl1paeNlwYfvKQlP"

if not AIRTABLE_API_KEY:
    print("HATA: AIRTABLE_TOKEN bulunamadı!")
    exit()

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

    # --- 1. FORUM MAKİNA ---
    print("\n[1/3] Forum Makina taranıyor...")
    page = 1
    continue_scraping = True
    while continue_scraping:
        url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        try:
            r = requests.get(url, timeout=20)
            soup = BeautifulSoup(r.content, "html.parser")
            items = soup.find_all("div", class_="title")
            if not items: break
            found_2026 = False
            for item in items:
                parent = item.find_parent()
                tarih = parent.find("div", class_="date").text if parent.find("div", class_="date") else ""
                if "2026" in tarih:
                    found_2026 = True
                    baslik = item.text.strip()
                    link = "https://www.forummakina.com.tr" + parent.find("a")["href"]
                    if link not in existing_urls and baslik.lower().strip() not in existing_titles:
                        table.create({"haber_basliği": baslik, "gorsel": parent.find("img")["src"] if parent.find("img") else "", "haber_metni": parent.find("span").text.strip() if parent.find("span") else "", "portal": "Forum Makina", "url": link})
                        print(f"Eklendi: {baslik}")
            if not found_2026: continue_scraping = False
            page += 1
        except: break

    # --- 2. LHT ---
    print("\n[2/3] LHT taranıyor...")
    page = 1
    continue_scraping = True
    while continue_scraping:
        url = f"https://www.lht.com.tr/kategori/haber/page/{page}/"
        try:
            r = requests.get(url, timeout=20)
            if r.status_code != 200: break
            soup = BeautifulSoup(r.content, "html.parser")
            articles = soup.find_all("article")
            found_2026 = False
            for article in articles:
                tarih = article.find("time", class_="entry-date")
                if tarih and "2026" in tarih.text:
                    found_2026 = True
                    baslik = article.find("h2").text.strip()
                    link = article.find("h2").find("a")["href"]
                    if link not in existing_urls and baslik.lower().strip() not in existing_titles:
                        table.create({"haber_basliği": baslik, "gorsel": article.find("img")["src"] if article.find("img") else "", "haber_metni": article.find("p", class_="post-excerpt").text.strip() if article.find("p") else "", "portal": "LHT", "url": link})
                        print(f"Eklendi: {baslik}")
            if not found_2026: continue_scraping = False
            page += 1
        except: break

    # --- 3. MAKİNA MARKET ---
    print("\n[3/3] Makina Market taranıyor...")
    page = 1
    continue_scraping = True
    while continue_scraping:
        url = f"https://makina-market.com.tr/category/haberler/page/{page}/"
        try:
            r = requests.get(url, timeout=20)
            if r.status_code != 200: break
            soup = BeautifulSoup(r.content, "html.parser")
            entries = soup.find_all("article")
            found_2026 = False
            for entry in entries:
                tarih = entry.find("div", class_="cs-meta-date")
                if tarih and "2026" in tarih.text:
                    found_2026 = True
                    baslik = entry.find("h2", class_="cs-entry__title").text.strip()
                    link = entry.find("h2", class_="cs-entry__title").find("a")["href"]
                    if link not in existing_urls and baslik.lower().strip() not in existing_titles:
                        table.create({"haber_basliği": baslik, "gorsel": entry.find("img")["src"] if entry.find("img") else "", "haber_metni": entry.find("div", class_="cs-entry__excerpt").text.strip() if entry.find("div") else "", "portal": "Makina Market", "url": link})
                        print(f"Eklendi: {baslik}")
            if not found_2026: continue_scraping = False
            page += 1
        except: break

if __name__ == "__main__":
    scrape_data()

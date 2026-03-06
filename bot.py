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
    """Mükerrer kontrolü için mevcut verileri hafızaya alır."""
    try:
        records = table.all()
        urls = [r['fields'].get('url') for r in records if 'url' in r['fields']]
        titles = [r['fields'].get('haber_basliği', '').lower().strip() for r in records]
        return urls, titles
    except: return [], []

# --- SİTE FONKSİYONLARI (Buraya yeni siteler eklenebilir) ---

def scrape_forum_makina(existing_urls, existing_titles):
    print("\n🔍 [SİTE: Forum Makina] Taranıyor...")
    page = 1
    while True:
        url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        print(f"📄 Sayfa {page} kontrol ediliyor...")
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
                        table.create({
                            "haber_basliği": baslik,
                            "gorsel": parent.find("img")["src"] if parent.find("img") else "",
                            "haber_metni": parent.find("span").text.strip() if parent.find("span") else "",
                            "portal": "Forum Makina",
                            "url": link
                        })
                        print(f"✅ Eklendi: {baslik[:50]}")
            
            if not found_2026: break
            page += 1
        except: break

# --- ANA ÇALIŞTIRICI (ORKESTRA ŞEFİ) ---

def main():
    # 1. Mevcut verileri bir kez çek
    existing_urls, existing_titles = get_existing_data()
    
    # 2. Siteleri sırayla çalıştır
    scrape_forum_makina(existing_urls, existing_titles)
    
    # Yarın buraya şunu ekleyebilirsin:
    # scrape_lht(existing_urls, existing_titles)
    # scrape_makina_market(existing_urls, existing_titles)

if __name__ == "__main__":
    main()
    print("\n

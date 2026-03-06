import os
import requests
from bs4 import BeautifulSoup
from pyairtable import Api
from dotenv import load_dotenv
from urllib.parse import urljoin, quote

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
        return urls
    except: return []

def scrape_forum_makina():
    existing_urls = get_existing_data()
    print(f"🚀 Tarama Başladı... Mevcut: {len(existing_urls)}")

    url = "https://www.forummakina.com.tr/tr/haberler"
    try:
        r = requests.get(url, timeout=20)
        soup = BeautifulSoup(r.content, "html.parser")
        items = soup.find_all("div", class_="title")
        
        for item in items:
            parent = item.find_parent()
            baslik = item.text.strip()
            link_tag = parent.find("a")
            link = urljoin("https://www.forummakina.com.tr", link_tag["href"]) if link_tag else ""

            if link not in existing_urls:
                # --- GÖRSEL TAMİRİ ---
                img_tag = parent.find("img")
                img_url = ""
                if img_tag:
                    raw_path = img_tag.get("src") or ""
                    # Boşlukları ve özel karakterleri %20 formatına çevir
                    if raw_path:
                        # Önce domaini ekle, sonra path kısmındaki boşlukları quote ile temizle
                        full_path = urljoin("https://www.forummakina.com.tr", raw_path)
                        # Sadece son kısımdaki boşlukları temizleyelim
                        img_url = full_url = full_path.replace(" ", "%20")

                print(f"🎬 Haber: {baslik[:30]}...")
                print(f"🖼️ URL: {img_url}")

                payload = {
                    "haber_basligi": baslik,
                    "gorsel": img_url,
                    "haber_metni": parent.find("span").text.strip() if parent.find("span") else "",
                    "portal": "Forum Makina",
                    "url": link
                }
                
                table.create(payload)
                print("✅ Başarıyla eklendi.")
                
    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    scrape_forum_makina()

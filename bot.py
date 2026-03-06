import os
import requests
from bs4 import BeautifulSoup
from pyairtable import Api
from dotenv import load_dotenv
from urllib.parse import urljoin, quote, urlparse

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
        return [r['fields'].get('url') for r in records if 'url' in r['fields']]
    except: return []

def safe_url_encode(url):
    """Linkteki boşlukları, parantezleri ve Türkçe karakterleri Airtable'ın seveceği hale getirir."""
    if not url: return ""
    # http'yi https yap (Airtable güvenli link sever)
    url = url.replace("http://", "https://")
    
    # Linki parçala ve sadece yol (path) kısmını kodla
    parsed = urlparse(url)
    encoded_path = quote(parsed.path)
    return f"https://{parsed.netloc}{encoded_path}"

def scrape_forum_makina():
    existing_urls = get_existing_data()
    print(f"🚀 Forum Makina Taraması Başladı...")

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
                # --- GÖRSEL TEMİZLEME OPERASYONU ---
                img_tag = parent.find("img")
                raw_img = img_tag.get("src") if img_tag else ""
                
                # Linki tam adrese çevir
                full_raw_url = urljoin("https://www.forummakina.com.tr", raw_img)
                # Boşlukları ve parantezleri temizle (v3)
                final_img_url = safe_url_encode(full_raw_url)

                print(f"🎬 İşleniyor: {baslik[:30]}...")
                print(f"🖼️ Temizlenmiş Link: {final_img_url}")

                payload = {
                    "haber_basligi": baslik,
                    "gorsel": final_img_url,
                    "haber_metni": parent.find("span").text.strip() if parent.find("span") else "",
                    "portal": "Forum Makina",
                    "url": link
                }
                
                table.create(payload)
                print("✅ Airtable'a gönderildi.")
                
    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    scrape_forum_makina()

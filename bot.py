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
    """Linkteki boşluk ve parantezleri Airtable'ın dosyayı indirebileceği hale getirir."""
    if not url: return ""
    # http'yi https yapıyoruz (Airtable güvenli bağlantıdan dosya çekmeyi sever)
    url = url.replace("http://", "https://")
    parsed = urlparse(url)
    # Sadece dosya yolunu (path) encode ediyoruz, domaini ellemiyoruz
    encoded_path = quote(parsed.path)
    return f"https://{parsed.netloc}{encoded_path}"

def scrape_forum_makina():
    existing_urls = get_existing_data()
    print(f"🚀 Forum Makina Taraması (Attachment Modu) Başladı...")

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
                img_tag = parent.find("img")
                raw_img = img_tag.get("src") if img_tag else ""
                
                # 1. Linki tam adrese çevir ve temizle
                full_raw_url = urljoin("https://www.forummakina.com.tr", raw_img)
                final_img_url = safe_url_encode(full_raw_url)

                print(f"🎬 İşleniyor: {baslik[:30]}...")
                print(f"🖼️ Hazırlanan Dosya Linki: {final_img_url}")

                # 2. KRİTİK NOKTA: Attachment formatı budur! 
                # Sadece link değil, [{"url": "link"}] şeklinde gönderilmeli.
                payload = {
                    "haber_basligi": baslik,
                    "gorsel": [{"url": final_img_url}], # Burası Attachment için özel format
                    "haber_metni": parent.find("span").text.strip() if parent.find("span") else "",
                    "portal": "Forum Makina",
                    "url": link
                }
                
                try:
                    table.create(payload)
                    print("✅ Resimle birlikte Airtable'a eklendi.")
                except Exception as e:
                    print(f"❌ Airtable Yazma Hatası: {e}")
                    # Eğer hata verirse, resimsiz denesin (Sütun tipi uyuşmazlığı kontrolü için)
                    print("⚠️ Resimsiz ekleme deneniyor...")
                    payload["gorsel"] = []
                    table.create(payload)
                
    except Exception as e:
        print(f"❌ Sistem Hatası: {e}")

if __name__ == "__main__":
    scrape_forum_makina()

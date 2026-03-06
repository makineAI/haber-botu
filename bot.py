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
    """Mükerrer kontrolü için mevcut URL ve Başlıkları çeker."""
    existing_urls = set()
    existing_titles = set()
    try:
        records = table.all()
        for r in records:
            fields = r.get('fields', {})
            u = fields.get('url', '').strip().lower()
            if u: existing_urls.add(u)
            t = fields.get('haber_basligi', '').strip().lower()
            if t: existing_titles.add(t)
        print(f"✅ Hafıza Güncellendi: {len(existing_urls)} kayıt bulundu.")
        return existing_urls, existing_titles
    except:
        return set(), set()

def clean_image_url(raw_url):
    """Boşluklu ve parantezli resim linklerini Airtable için tamir eder."""
    if not raw_url: return ""
    url = raw_url.replace("http://", "https://")
    # Linki parçalara ayırıp sadece dosya adını (boşluklar dahil) encode eder
    base_part = "/".join(url.split("/")[:-1]) + "/"
    file_part = quote(url.split("/")[-1])
    return base_part + file_part

def scrape_forum_makina():
    ex_urls, ex_titles = get_existing_data()
    print("🚀 Tarama Başlatıldı...")

    # 1'den 15. sayfaya kadar 2026 haberlerini ara
    for page in range(1, 16):
        url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        print(f"📄 Sayfa {page} taranıyor...")
        try:
            r = requests.get(url, timeout=20)
            soup = BeautifulSoup(r.content, "html.parser")
            news_items = soup.find_all("li", class_="news")
            
            if not news_items: break

            for item in news_items:
                date_div = item.find("div", class_="date")
                tarih = date_div.text.strip() if date_div else ""
                
                if "2026" in tarih:
                    title_div = item.find("div", class_="title")
                    baslik = title_div.text.strip() if title_div else ""
                    link_tag = item.find("a")
                    link = urljoin("https://www.forummakina.com.tr", link_tag["href"]) if link_tag else ""
                    
                    # --- Mükerrer Kontrolü ---
                    if link.strip().lower() in ex_urls or baslik.strip().lower() in ex_titles:
                        continue

                    # Resim ve Metin İşleme
                    img_tag = item.find("img")
                    final_img = clean_image_url(img_tag.get("src")) if img_tag else ""
                    metin = item.find("span").get_text(strip=True).replace("devamı", "")

                    payload = {
                        "haber_basligi": baslik,
                        "gorsel": [{"url": final_img}] if final_img else [],
                        "haber_metni": metin,
                        "portal": "Forum Makina",
                        "url": link
                    }

                    table.create(payload)
                    print(f"✅ Eklendi: {baslik[:40]}...")
                    ex_urls.add(link.strip().lower())
                    ex_titles.add(baslik.strip().lower())
        except:
            continue

if __name__ == "__main__":
    scrape_forum_makina()
    print("🏁 İşlem Tamamlandı.")

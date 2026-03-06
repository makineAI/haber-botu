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

def get_existing_urls():
    try:
        records = table.all()
        return [r['fields'].get('url') for r in records if 'url' in r['fields']]
    except: return []

def clean_image_url(raw_url):
    """Resim linkindeki boşlukları temizler ve HTTPS yapar."""
    if not raw_url: return ""
    # Airtable için http -> https çevrimi ve boşlukları %20 yapma
    url = raw_url.replace("http://", "https://")
    # Linkin son kısmındaki boşlukları kodla (quote)
    base_part = "/".join(url.split("/")[:-1]) + "/"
    file_part = url.split("/")[-1]
    return base_part + quote(file_part)

def scrape_forum_makina():
    existing_urls = get_existing_urls()
    print("🚀 Tarama başlatıldı...")

    # Kaç sayfa taranacağını buradan ayarlayabilirsin (Örn: 1-15 arası tüm sayfalar)
    for page in range(1, 11): 
        url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        print(f"📄 Sayfa {page} taranıyor...")
        
        try:
            r = requests.get(url, timeout=20)
            soup = BeautifulSoup(r.content, "html.parser")
            
            # Senin verdiğin HTML yapısına göre li.news etiketlerini buluyoruz
            news_items = soup.find_all("li", class_="news")
            
            if not news_items:
                print(f"⚠️ Sayfa {page}'de haber bulunamadı, durduruluyor.")
                break

            for item in news_items:
                # 1. Tarih Kontrolü
                date_div = item.find("div", class_="date")
                tarih = date_div.text.strip() if date_div else ""
                
                # Sadece 2026 haberlerini al
                if "2026" in tarih:
                    # 2. Başlık ve Link
                    title_div = item.find("div", class_="title")
                    baslik = title_div.text.strip() if title_div else ""
                    
                    link_tag = item.find("a")
                    link = urljoin("https://www.forummakina.com.tr", link_tag["href"]) if link_tag else ""

                    # Eğer bu haber daha önce eklenmediyse
                    if link not in existing_urls:
                        # 3. Resim İşleme (Kritik Nokta)
                        img_tag = item.find("img")
                        raw_img_url = img_tag.get("src") if img_tag else ""
                        final_img = clean_image_url(raw_img_url)

                        # 4. Haber Metni
                        text_span = item.find("span")
                        # "devamı" yazısını metinden temizle
                        metin = text_span.text.replace("devamı", "").strip() if text_span else ""

                        payload = {
                            "haber_basligi": baslik,
                            "gorsel": [{"url": final_img}] if final_img else [],
                            "haber_metni": metin,
                            "portal": "Forum Makina",
                            "url": link
                        }

                        try:
                            table.create(payload)
                            print(f"✅ Eklendi: {baslik[:40]}...")
                            existing_urls.append(link)
                        except Exception as e:
                            print(f"❌ Airtable Hatası ({baslik[:20]}): {e}")
                
        except Exception as e:
            print(f"❌ Bağlantı hatası: {e}")
            break

if __name__ == "__main__":
    scrape_forum_makina()
    print("🏁 İşlem tamamlandı.")

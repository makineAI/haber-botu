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
        titles = [r['fields'].get('haber_basligi', '').lower().strip() for r in records]
        return urls, titles
    except Exception as e:
        print(f"Airtable verisi alınamadı: {e}")
        return [], []

def scrape_forum_makina(existing_urls, existing_titles):
    print("\n--- Forum Makina Taraması (Görsel Odaklı) ---")
    page = 1
    while True:
        url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        print(f"📄 Sayfa {page} kontrol ediliyor...")
        try:
            r = requests.get(url, timeout=20)
            soup = BeautifulSoup(r.content, "html.parser")
            
            # Forum Makina'da haber blokları genellikle .news-card veya benzeri kapsayıcılardadır. 
            # Başlık divinden yukarı çıkıp kapsayıcıyı buluyoruz.
            items = soup.find_all("div", class_="title")
            if not items: break
            
            found_2026 = False
            for item in items:
                parent = item.find_parent()
                tarih_div = parent.find("div", class_="date")
                tarih = tarih_div.text.strip() if tarih_div else ""
                
                if "2026" in tarih:
                    found_2026 = True
                    baslik = item.text.strip()
                    link_tag = parent.find("a")
                    link = "https://www.forummakina.com.tr" + link_tag["href"] if link_tag else ""
                    
                    if link not in existing_urls and baslik.lower().strip() not in existing_titles:
                        # --- GÖRSEL BULMA MANTIĞI ---
                        img_tag = parent.find("img")
                        img_url = ""
                        if img_tag:
                            # Bazı siteler 'src' yerine 'data-src' kullanır, ikisini de kontrol edelim
                            raw_img = img_tag.get("src") or img_tag.get("data-src") or ""
                            
                            if raw_img:
                                if raw_img.startswith("http"):
                                    img_url = raw_img
                                elif raw_img.startswith("/"):
                                    img_url = "https://www.forummakina.com.tr" + raw_img
                                else:
                                    img_url = "https://www.forummakina.com.tr/" + raw_img

                        print(f"✅ Haber: {baslik[:30]}... | Görsel: {img_url}")

                        payload = {
                            "haber_basligi": baslik,
                            "gorsel": img_url,
                            "haber_metni": parent.find("span").text.strip() if parent.find("span") else "",
                            "portal": "Forum Makina",
                            "url": link
                        }
                        
                        try:
                            table.create(payload)
                        except Exception as e:
                            print(f"❌ Airtable Yazma Hatası: {e}")
            
            if not found_2026: break
            page += 1
        except Exception as e:
            print(f"❌ Hata: {e}")
            break

if __name__ == "__main__":
    ex_urls, ex_titles = get_existing_data()
    scrape_forum_makina(ex_urls, ex_titles)
    print("\n🏁 İşlem Tamamlandı.")

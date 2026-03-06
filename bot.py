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

if not AIRTABLE_API_KEY:
    print("HATA: AIRTABLE_TOKEN bulunamadı!")
    exit(1)

api = Api(AIRTABLE_API_KEY)
table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_ID)

def get_existing_data():
    try:
        records = table.all()
        urls = [r['fields'].get('url') for r in records if 'url' in r['fields']]
        titles = [r['fields'].get('haber_basliği', '').lower().strip() for r in records]
        return urls, titles
    except Exception as e:
        print(f"Airtable Hatası: {e}")
        return [], []

def scrape_forum_makina(existing_urls, existing_titles):
    print("--- Forum Makina Taraması Başladı ---")
    page = 1
    while True:
        url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        print(f"Sayfa {page} kontrol ediliyor...")
        try:
            r = requests.get(url, timeout=20)
            if r.status_code != 200: break
            soup = BeautifulSoup(r.content, "html.parser")
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
                    link = "https://www.forummakina.com.tr" + parent.find("a")["href"]
                    
                    if link not in existing_urls and baslik.lower().strip() not in existing_titles:
                        table.create({
                            "haber_basliği": baslik,
                            "gorsel": parent.find("img")["src"] if parent.find("img") else "",
                            "haber_metni": parent.find("span").text.strip() if parent.find("span") else "",
                            "portal": "Forum Makina",
                            "url": link
                        })
                        print(f"Eklendi: {baslik[:50]}")
                        existing_urls.append(link)
                        existing_titles.append(baslik.lower().strip())
            
            if not found_2026: 
                print("2026 haberi kalmadı, durduruluyor.")
                break
            page += 1
        except Exception as e:
            print(f"Hata oluştu: {e}")
            break

if __name__ == "__main__":
    ex_urls, ex_titles = get_existing_data()
    scrape_forum_makina(ex_urls, ex_titles)
    print("Islem Tamamlandi.")

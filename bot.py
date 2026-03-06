import os
import requests
from bs4 import BeautifulSoup
from pyairtable import Api
from dotenv import load_dotenv

load_dotenv()

# --- AYARLAR ---
AIRTABLE_API_KEY = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = "appC4JNkqLfVCEcna"
AIRTABLE_TABLE_ID = "tbl1paeNlwYfvKQlP" # ID değişmediği için bu kalsın

api = Api(AIRTABLE_API_KEY)
table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_ID)

def get_existing_data():
    try:
        records = table.all()
        # Sütun isimlerini burada da 'i' harfiyle güncelledik
        urls = [r['fields'].get('url') for r in records if 'url' in r['fields']]
        titles = [r['fields'].get('haber_basligi', '').lower().strip() for r in records]
        return urls, titles
    except: return [], []

def scrape_forum_makina(existing_urls, existing_titles):
    print("\n--- Forum Makina Taraması Başladı ---")
    page = 1
    while True:
        url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        print(f"Sayfa {page} taranıyor...")
        try:
            r = requests.get(url, timeout=20)
            soup = BeautifulSoup(r.content, "html.parser")
            items = soup.find_all("div", class_="title")
            if not items: break
            
            found_2026 = False
            for item in items:
                parent = item.find_parent()
                tarih = parent.find("div", class_="date").text.strip() if parent.find("div", class_="date") else ""
                
                if "2026" in tarih:
                    found_2026 = True
                    baslik = item.text.strip()
                    link = "https://www.forummakina.com.tr" + parent.find("a")["href"]
                    
                    if link not in existing_urls and baslik.lower().strip() not in existing_titles:
                        # BURADAKİ ANAHTARLAR AİRTABLE SÜTUNLARIYLA AYNI OLMALI
                        payload = {
                            "haber_basligi": baslik, # 'i' harfine dikkat!
                            "gorsel": parent.find("img")["src"] if parent.find("img") else "",
                            "haber_metni": parent.find("span").text.strip() if parent.find("span") else "",
                            "portal": "Forum Makina",
                            "url": link
                        }
                        
                        try:
                            table.create(payload)
                            print(f"✅ Eklendi: {baslik[:40]}...")
                            existing_urls.append(link)
                            existing_titles.append(baslik.lower().strip())
                        except Exception as e:
                            print(f"❌ Airtable Hatası: {e}")
                            return # Hatayı gör diye durduruyoruz
            
            if not found_2026: break
            page += 1
        except Exception as e:
            print(f"Bağlantı Hatası: {e}")
            break

if __name__ == "__main__":
    ex_urls, ex_titles = get_existing_data()
    scrape_forum_makina(ex_urls, ex_titles)

import os
import requests
from bs4 import BeautifulSoup
from pyairtable import Api
from dotenv import load_dotenv
from urllib.parse import quote # Boşlukları %20 yapmak için

load_dotenv()

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
    except: return [], []

def fix_url(url):
    """Linkteki boşlukları ve Türkçe karakterleri URL formatına çevirir."""
    if not url: return ""
    # Sadece path kısmını encode etmeliyiz ki http:// bozulmasın
    base = "https://www.forummakina.com.tr"
    path = url.replace(base, "").replace("http://www.forummakina.com.tr", "")
    return base + quote(path)

def scrape_forum_makina(existing_urls, existing_titles):
    print("\n--- Forum Makina Taraması (Görsel Link Tamiri Aktif) ---")
    page = 1
    while True:
        url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
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
                        # GÖRSEL ÇEKME VE TAMİR ETME
                        img_tag = parent.find("img")
                        raw_img = img_tag.get("src") if img_tag else ""
                        
                        # Boşluklu linki temizle
                        clean_img_url = fix_url(raw_img)

                        print(f"✅ İşleniyor: {baslik[:30]}...")
                        print(f"🔗 Görsel Linki: {clean_img_url}")

                        payload = {
                            "haber_basligi": baslik,
                            "gorsel": clean_img_url,
                            "haber_metni": parent.find("span").text.strip() if parent.find("span") else "",
                            "portal": "Forum Makina",
                            "url": link
                        }
                        
                        table.create(payload)
                        existing_urls.append(link)
                        existing_titles.append(baslik.lower().strip())
            
            if not found_2026: break
            page += 1
        except Exception as e:
            print(f"Hata: {e}")
            break

if __name__ == "__main__":
    ex_urls, ex_titles = get_existing_data()
    scrape_forum_makina(ex_urls, ex_titles)

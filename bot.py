import os
import requests
from bs4 import BeautifulSoup
from pyairtable import Api
from dotenv import load_dotenv
from urllib.parse import quote

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

def fix_image_url(raw_url):
    """Linkteki tüm sorunları (http, boşluk, eksik domain) giderir."""
    if not raw_url: return ""
    
    # 1. Domain eksikse tamamla ve zorunlu HTTPS yap
    if raw_url.startswith('/'):
        full_url = "https://www.forummakina.com.tr" + raw_url
    elif raw_url.startswith('http'):
        full_url = raw_url.replace('http://', 'https://')
    else:
        full_url = "https://www.forummakina.com.tr/" + raw_url
    
    # 2. URL'yi parçalara ayırıp boşlukları %20 yap (quote kullanıyoruz)
    # Sadece path kısmını encode etmek en güvenlisidir
    parts = full_url.split('forummakina.com.tr')
    if len(parts) > 1:
        clean_path = quote(parts[1])
        return "https://www.forummakina.com.tr" + clean_path
    return full_url

def scrape_forum_makina(existing_urls, existing_titles):
    print("\n--- Forum Makina Taraması (Görsel Fix v3) ---")
    page = 1
    while True:
        url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        print(f"📄 Sayfa {page} taranıyor...")
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
                        # GÖRSEL İŞLEME
                        img_tag = parent.find("img")
                        raw_img_path = img_tag.get("src") if img_tag else ""
                        
                        final_img_url = fix_image_url(raw_img_path)

                        print(f"🎬 Haber: {baslik[:30]}...")
                        print(f"🖼️ Üretilen Link: {final_img_url}")

                        payload = {
                            "haber_basligi": baslik,
                            "gorsel": final_img_url,
                            "haber_metni": parent.find("span").text.strip() if parent.find("span") else "",
                            "portal": "Forum Makina",
                            "url": link
                        }
                        
                        table.create(payload)
                        print("✅ Airtable'a gönderildi.")
                        existing_urls.append(link)
                        existing_titles.append(baslik.lower().strip())
            
            if not found_2026: break
            page += 1
        except Exception as e:
            print(f"❌ Hata: {e}")
            break

if __name__ == "__main__":
    ex_urls, ex_titles = get_existing_data()
    scrape_forum_makina(ex_urls, ex_titles)

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
    ex_urls = set()
    ex_titles = set()
    try:
        records = table.all()
        for r in records:
            f = r.get('fields', {})
            u = f.get('url', '').strip().lower()
            t = f.get('haber_basligi', '').strip().lower()
            if u: ex_urls.add(u)
            if t: ex_titles.add(t)
        return ex_urls, ex_titles
    except: return set(), set()

def clean_img(url, base_url):
    if not url: return ""
    full_url = urljoin(base_url, url).replace("http://", "https://")
    parts = full_url.split("/")
    file_part = quote(parts[-1])
    return "/".join(parts[:-1]) + "/" + file_part

# --- SİTE 1: FORUM MAKİNA (Mevcut Düzen) ---
def scrape_forum_makina(ex_urls, ex_titles):
    print("\n🔍 [TARAMA] Forum Makina...")
    for page in range(1, 6):
        try:
            r = requests.get(f"https://www.forummakina.com.tr/tr/haberler?page={page}", timeout=20)
            soup = BeautifulSoup(r.content, "html.parser")
            for item in soup.find_all("li", class_="news"):
                tarih = item.find("div", class_="date").text if item.find("div", class_="date") else ""
                if "2026" in tarih:
                    baslik = item.find("div", class_="title").text.strip()
                    link = urljoin("https://www.forummakina.com.tr", item.find("a")["href"])
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img = clean_img(item.find("img")["src"], "https://www.forummakina.com.tr") if item.find("img") else ""
                    metin = item.find("span").get_text(strip=True).replace("devamı", "")
                    table.create({"haber_basligi": baslik, "gorsel": [{"url": img}] if img else [], "haber_metni": metin, "portal": "Forum Makina", "url": link})
                    print(f"✅ Forum Makina: {baslik[:30]}...")
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: break

# --- SİTE 2: LHT (LOJİSTİK HATTI - YENİ DİNAMİK) ---
def scrape_lht(ex_urls, ex_titles):
    print("\n🔍 [TARAMA] LHT (Lojistik Hattı)...")
    # LHT WordPress tabanlı olduğu için sayfalama paged=2 şeklinde gider
    for page in range(1, 4): 
        url = f"https://www.lht.com.tr/kategori/haber/page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(r.content, "html.parser")
            # Verdiğin koda göre article etiketlerini buluyoruz
            articles = soup.find_all("article")
            
            for art in articles:
                # Tarih kontrolü (time etiketindeki datetime'dan 2026'yı yakala)
                time_tag = art.find("time")
                dt = time_tag.get("datetime", "") if time_tag else ""
                
                if "2026" in dt:
                    title_tag = art.find("h2", class_="entry-title")
                    if not title_tag: continue
                    baslik = title_tag.text.strip()
                    link = title_tag.find("a")["href"]
                    
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    
                    # Görsel (post-thumb içindeki img)
                    img_tag = art.find("div", class_="post-thumb")
                    img_src = img_tag.find("img")["src"] if img_tag and img_tag.find("img") else ""
                    final_img = clean_img(img_src, "https://www.lht.com.tr")
                    
                    # Özet metin
                    excerpt = art.find("p", class_="post-excerpt")
                    metin = excerpt.text.strip() if excerpt else ""
                    
                    table.create({
                        "haber_basligi": baslik, 
                        "gorsel": [{"url": final_img}] if final_img else [], 
                        "haber_metni": metin, 
                        "portal": "LHT", 
                        "url": link
                    })
                    print(f"✅ LHT: {baslik[:30]}...")
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except Exception as e:
            print(f"⚠️ LHT Sayfa {page} hatası: {e}")
            break

if __name__ == "__main__":
    urls, titles = get_existing_data()
    scrape_forum_makina(urls, titles)
    scrape_lht(urls, titles)
    print("\n🏁 İşlem Tamamlandı.")

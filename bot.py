import os
import requests
from bs4 import BeautifulSoup
from pyairtable import Api
from dotenv import load_dotenv
from urllib.parse import urljoin, quote

load_dotenv()

# --- AYARLAR (Lütfen Buraya Dokunma) ---
AIRTABLE_API_KEY = os.environ.get('AIRTABLE_TOKEN')
AIRTABLE_BASE_ID = "appC4JNkqLfVCEcna"
AIRTABLE_TABLE_ID = "tbl1paeNlwYfvKQlP"

api = Api(AIRTABLE_API_KEY)
table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_ID)

# --- YARDIMCI FONKSİYONLAR ---
def get_existing_data():
    ex_urls, ex_titles = set(), set()
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

# --- 1. SİTE: FORUM MAKİNA ---
def scrape_forum_makina(ex_urls, ex_titles):
    print("\n🔍 [1/3] Forum Makina Taraması...")
    for page in range(1, 11):
        try:
            r = requests.get(f"https://www.forummakina.com.tr/tr/haberler?page={page}", timeout=20)
            soup = BeautifulSoup(r.content, "html.parser")
            items = soup.find_all("li", class_="news")
            if not items: break
            for item in items:
                tarih = item.find("div", class_="date").get_text(strip=True) if item.find("div", class_="date") else ""
                if "2026" in tarih:
                    baslik = item.find("div", class_="title").get_text(strip=True)
                    link = urljoin("https://www.forummakina.com.tr", item.find("a")["href"])
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img = clean_img(item.find("img")["src"], "https://www.forummakina.com.tr") if item.find("img") else ""
                    table.create({"haber_basligi": baslik, "gorsel": [{"url": img}] if img else [], "portal": "Forum Makina", "url": link})
                    print(f"✅ Eklendi: {baslik[:30]}")
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: break

# --- 2. SİTE: LHT ---
def scrape_lht(ex_urls, ex_titles):
    print("\n🔍 [2/3] LHT Taraması...")
    for page in range(1, 11):
        try:
            r = requests.get(f"https://www.lht.com.tr/kategori/haber/page/{page}/", timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code != 200: break
            soup = BeautifulSoup(r.content, "html.parser")
            articles = soup.find_all("article")
            if not articles: break
            for art in articles:
                dt = art.find("time").get("datetime", "") if art.find("time") else ""
                if "2026" in dt:
                    title_tag = art.find("h2", class_="entry-title")
                    baslik = title_tag.get_text(strip=True)
                    link = title_tag.find("a")["href"]
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img_src = art.find("div", class_="post-thumb").find("img")["src"] if art.find("div", class_="post-thumb") else ""
                    table.create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, "https://www.lht.com.tr")}] if img_src else [], "portal": "LHT", "url": link})
                    print(f"✅ Eklendi: {baslik[:30]}")
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: break

# --- 3. SİTE: MAKİNA MARKET (TÜM KATEGORİLER) ---
def scrape_makina_market_all(ex_urls, ex_titles):
    kategoriler = {
        "haberler": "Makina Market - Haber",
        "saha-roportaji": "Makina Market - Saha Röportajı",
        "roportaj": "Makina Market - Röportaj",
        "proje-haberi": "Makina Market - Proje Haberi",
        "urun-tanitimi": "Makina Market - Ürün Tanıtımı",
        "yeni-urun": "Makina Market - Yeni Ürün"
    }
    
    headers = {'User-Agent': 'Mozilla/5.0'}

    for slug, portal_adi in kategoriler.items():
        print(f"\n🔍 [3/3] {portal_adi} Taranıyor...")
        for page in range(1, 11):
            url = f"https://makina-market.com.tr/category/{slug}/page/{page}/"
            try:
                r = requests.get(url, timeout=20, headers=headers)
                if r.status_code != 200: break
                soup = BeautifulSoup(r.content, "html.parser")
                articles = soup.find_all("article")
                if not articles: break
                
                for art in articles:
                    tarih = art.find("div", class_="cs-meta-date").get_text(strip=True) if art.find("div", class_="cs-meta-date") else ""
                    if "2026" in tarih:
                        title_tag = art.find("h2", class_="cs-entry__title")
                        baslik = title_tag.get_text(strip=True)
                        link = title_tag.find("a")["href"]
                        if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                        
                        img_div = art.find("div", class_="cs-overlay-background")
                        img_src = img_div.find("img")["src"] if img_div and img_div.find("img") else ""
                        
                        table.create({
                            "haber_basligi": baslik,
                            "gorsel": [{"url": clean_img(img_src, "https://makina-market.com.tr")}] if img_src else [],
                            "portal": portal_adi,
                            "url": link
                        })
                        print(f"✅ Eklendi: {baslik[:30]}")
                        ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
            except: break

# --- ANA ÇALIŞTIRICI ---
if __name__ == "__main__":
    print("🚀 Haber Botu Başlatılıyor...")
    urls, titles = get_existing_data()
    
    scrape_forum_makina(urls, titles)
    scrape_lht(urls, titles)
    scrape_makina_market_all(urls, titles)
    
    print("\n🏁 Tüm işlemler bitti. Airtable'ı kontrol et!")

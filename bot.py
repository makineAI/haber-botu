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

# --- SİTE 1: FORUM MAKİNA ---
def scrape_forum_makina(ex_urls, ex_titles):
    print("\n🔍 [1/3] Forum Makina Taraması...")
    for page in range(1, 11):
        try:
            r = requests.get(f"https://www.forummakina.com.tr/tr/haberler?page={page}", timeout=20)
            soup = BeautifulSoup(r.content, "html.parser")
            items = soup.find_all("li", class_="news")
            if not items: break
            for item in items:
                date_div = item.find("div", class_="date")
                tarih = date_div.get_text(strip=True) if date_div else ""
                if "2026" in tarih:
                    title_div = item.find("div", class_="title")
                    baslik = title_div.get_text(strip=True) if title_div else ""
                    link_tag = item.find("a")
                    link = urljoin("https://www.forummakina.com.tr", link_tag["href"]) if link_tag else ""
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img_tag = item.find("img")
                    img = clean_img(img_tag["src"], "https://www.forummakina.com.tr") if img_tag else ""
                    metin = item.find("span").get_text(strip=True).replace("devamı", "") if item.find("span") else ""
                    table.create({"haber_basligi": baslik, "gorsel": [{"url": img}] if img else [], "haber_metni": metin, "portal": "Forum Makina", "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: break

# --- SİTE 2: LHT (LOJİSTİK HATTI) ---
def scrape_lht(ex_urls, ex_titles):
    print("\n🔍 [2/3] LHT Taraması...")
    for page in range(1, 11):
        url = f"https://www.lht.com.tr/kategori/haber/page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code != 200: break
            soup = BeautifulSoup(r.content, "html.parser")
            articles = soup.find_all("article")
            if not articles: break
            for art in articles:
                time_tag = art.find("time")
                dt = time_tag.get("datetime", "") if time_tag else ""
                if "2026" in dt:
                    title_tag = art.find("h2", class_="entry-title")
                    if not title_tag: continue
                    baslik = title_tag.get_text(strip=True)
                    link = title_tag.find("a")["href"]
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img_thumb = art.find("div", class_="post-thumb")
                    img_src = img_thumb.find("img")["src"] if img_thumb and img_thumb.find("img") else ""
                    final_img = clean_img(img_src, "https://www.lht.com.tr")
                    excerpt = art.find("p", class_="post-excerpt")
                    metin = excerpt.get_text(strip=True) if excerpt else ""
                    table.create({"haber_basligi": baslik, "gorsel": [{"url": final_img}] if final_img else [], "haber_metni": metin, "portal": "LHT", "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: break

# --- SİTE 3: MAKİNA MARKET ---
def scrape_makina_market(ex_urls, ex_titles):
    print("\n🔍 [3/3] Makina Market - Haber Taraması...")
    for page in range(1, 11): # 10 sayfa tarar
        url = f"https://makina-market.com.tr/category/haberler/page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code != 200: break
            soup = BeautifulSoup(r.content, "html.parser")
            articles = soup.find_all("article")
            if not articles: break
            for art in articles:
                date_div = art.find("div", class_="cs-meta-date")
                tarih = date_div.get_text(strip=True) if date_div else ""
                if "2026" in tarih:
                    title_tag = art.find("h2", class_="cs-entry__title")
                    if not title_tag: continue
                    baslik = title_tag.get_text(strip=True)
                    link = title_tag.find("a")["href"]
                    
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    
                    img_div = art.find("div", class_="cs-overlay-background")
                    img_src = img_div.find("img")["src"] if img_div and img_div.find("img") else ""
                    final_img = clean_img(img_src, "https://makina-market.com.tr")
                    excerpt = art.find("div", class_="cs-entry__excerpt")
                    metin = excerpt.get_text(strip=True) if excerpt else ""
                    
                    # Portal ismi güncellendi
                    table.create({
                        "haber_basligi": baslik, 
                        "gorsel": [{"url": final_img}] if final_img else [], 
                        "haber_metni": metin, 
                        "portal": "Makina Market - Haber", 
                        "url": link
                    })
                    print(f"✅ Makina Market - Haber: {baslik[:30]}...")
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: break

# --- SİTE 4: MAKİNA MARKET - SAHA RÖPORTAJI ---
def scrape_saha_roportaji(ex_urls, ex_titles):
    print("\n🔍 [4/4] Makina Market - Saha Röportajı Taraması...")
    for page in range(1, 11):
        url = f"https://makina-market.com.tr/category/saha-roportaji/page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code != 200: break
            soup = BeautifulSoup(r.content, "html.parser")
            articles = soup.find_all("article")
            if not articles: break
            for art in articles:
                date_div = art.find("div", class_="cs-meta-date")
                tarih = date_div.get_text(strip=True) if date_div else ""
                if "2026" in tarih:
                    title_tag = art.find("h2", class_="cs-entry__title")
                    if not title_tag: continue
                    baslik = title_tag.get_text(strip=True)
                    link = title_tag.find("a")["href"]
                    
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    
                    img_div = art.find("div", class_="cs-overlay-background")
                    img_src = img_div.find("img")["src"] if img_div and img_div.find("img") else ""
                    final_img = clean_img(img_src, "https://makina-market.com.tr")
                    excerpt = art.find("div", class_="cs-entry__excerpt")
                    metin = excerpt.get_text(strip=True) if excerpt else ""
                    
                    table.create({
                        "haber_basligi": baslik, 
                        "gorsel": [{"url": final_img}] if final_img else [], 
                        "haber_metni": metin, 
                        "portal": "Makina Market - Saha Röportajı", 
                        "url": link
                    })
                    print(f"✅ Saha Röportajı: {baslik[:30]}...")
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: break

if __name__ == "__main__":
    urls, titles = get_existing_data()
    scrape_forum_makina(urls, titles)
    scrape_lht(urls, titles)
    scrape_makina_market(urls, titles)
    scrape_saha_roportaji(urls, titles) # <-- Bu yeni satırı ekledin
    print("\n🏁 İşlem Tamamlandı. Tüm portallar güncel!")

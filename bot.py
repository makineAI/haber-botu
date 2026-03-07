import os
import requests
from bs4 import BeautifulSoup
from pyairtable import Api
from dotenv import load_dotenv
from urllib.parse import urljoin, quote
from datetime import datetime

load_dotenv()
CURRENT_YEAR = str(datetime.now().year)

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
    print(f"\n🔍 [1/8] Forum Makina ({CURRENT_YEAR}) Taraması...")
    page = 1
    while True:
        url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        try:
            r = requests.get(url, timeout=20)
            soup = BeautifulSoup(r.content, "html.parser")
            items = soup.find_all("li", class_="news")
            if not items: break
            found_year = False
            for item in items:
                date_div = item.find("div", class_="date")
                tarih = date_div.get_text(strip=True) if date_div else ""
                if CURRENT_YEAR in tarih:
                    found_year = True
                    title_div = item.find("div", class_="title")
                    baslik = title_div.get_text(strip=True) if title_div else ""
                    link = urljoin("https://www.forummakina.com.tr", item.find("a")["href"])
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img = clean_img(item.find("img")["src"], url) if item.find("img") else ""
                    metin = item.find("span").get_text(strip=True).replace("devamı", "") if item.find("span") else ""
                    table.create({"haber_basligi": baslik, "gorsel": [{"url": img}] if img else [], "haber_metni": metin, "portal": "Forum Makina", "url": link})
                    print(f"✅ Forum Makina: {baslik[:30]}")
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
            if not found_year: break
            page += 1
        except: break

# --- SİTE 2: LHT ---
def scrape_lht(ex_urls, ex_titles):
    print(f"\n🔍 [2/8] LHT ({CURRENT_YEAR}) Taraması...")
    page = 1
    while True:
        url = f"https://www.lht.com.tr/kategori/haber/page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code != 200: break
            soup = BeautifulSoup(r.content, "html.parser")
            articles = soup.find_all("article")
            if not articles: break
            found_year = False
            for art in articles:
                dt = art.find("time").get("datetime", "") if art.find("time") else ""
                if CURRENT_YEAR in dt:
                    found_year = True
                    title_tag = art.find("h2", class_="entry-title")
                    baslik = title_tag.get_text(strip=True)
                    link = title_tag.find("a")["href"]
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img_src = art.find("img")["src"] if art.find("img") else ""
                    table.create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, url)}] if img_src else [], "haber_metni": art.find("p", class_="post-excerpt").get_text(strip=True) if art.find("p", class_="post-excerpt") else "", "portal": "LHT", "url": link})
                    print(f"✅ LHT: {baslik[:30]}")
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
            if not found_year: break
            page += 1
        except: break

# --- MAKİNA MARKET ANA MOTORU (HTML Yapısına Tam Uyumlu) ---
def scrape_mm_category(ex_urls, ex_titles, cat_slug, portal_name, step_info):
    print(f"\n🔍 [{step_info}] {portal_name} ({CURRENT_YEAR}) Taraması...")
    page = 1
    # User-Agent'ı daha güncel bir tarayıcı gibi yapalım
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    
    while True:
        url = f"https://makina-market.com.tr/category/{cat_slug}/page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers=headers)
            if r.status_code != 200: 
                break
                
            soup = BeautifulSoup(r.content, "html.parser")
            # Makina Market makalelerini bul
            articles = soup.find_all("article")
            if not articles: break
            
            found_year_in_page = False
            for art in articles:
                # 1. Tarih Tespiti
                date_div = art.find("div", class_="cs-meta-date")
                tarih = date_div.get_text(strip=True) if date_div else ""
                
                # Eğer tarih bu yıla aitse işle
                if CURRENT_YEAR in tarih:
                    found_year_in_page = True
                    
                    # 2. Başlık ve Link
                    title_tag = art.find("h2", class_="cs-entry__title")
                    if not title_tag: continue
                    baslik = title_tag.get_text(strip=True)
                    link = title_tag.find("a")["href"]
                    
                    # Mükerrer Kontrolü
                    if link.lower() in ex_urls or baslik.lower() in ex_titles:
                        continue
                    
                    # 3. Görsel Çekme (Paylaştığın HTML'deki cs-overlay-background yapısına göre)
                    img_src = ""
                    # Önce overlay içindeki resmi dene
                    overlay_img = art.find("div", class_="cs-overlay-background")
                    if overlay_img and overlay_img.find("img"):
                        img_src = overlay_img.find("img").get("src") or overlay_img.find("img").get("data-src")
                    
                    # Eğer bulamazsa herhangi bir img ara
                    if not img_src and art.find("img"):
                        img_src = art.find("img").get("src")
                    
                    final_img = clean_img(img_src, "https://makina-market.com.tr")
                    
                    # 4. Haber Metni (Excerpt)
                    metin_div = art.find("div", class_="cs-entry__excerpt")
                    metin = metin_div.get_text(strip=True) if metin_div else ""
                    
                    # 5. Airtable'a Gönder
                    table.create({
                        "haber_basligi": baslik,
                        "gorsel": [{"url": final_img}] if final_img else [],
                        "haber_metni": metin,
                        "portal": portal_name,
                        "url": link
                    })
                    print(f"✅ Eklendi: {baslik[:40]}...")
                    
                    # Listeyi güncelle
                    ex_urls.add(link.lower())
                    ex_titles.add(baslik.lower())
            
            # Eğer bu sayfada hiç 2026 haberi yoksa, artık eski sayfalara geçmişizdir
            if not found_year_in_page:
                print(f"   ℹ️ {CURRENT_YEAR} yılı içerikleri bitti.")
                break
                
            page += 1
        except Exception as e:
            print(f"   ⚠️ Hata oluştu: {e}")
            break

if __name__ == "__main__":
    urls, titles = get_existing_data()
    
    # 1. Forum Makina
    scrape_forum_makina(urls, titles)
    
    # 2. LHT
    scrape_lht(urls, titles)
    
    # 3-8. Makina Market Kategorileri (Her biri bağımsız çalışır)
    mm_cats = [
        ("haberler", "Makina Market - Haber", "3/8"),
        ("saha-roportaji", "Makina Market - Saha Röportajı", "4/8"),
        ("roportaj", "Makina Market - Röportaj", "5/8"),
        ("proje-haberi", "Makina Market - Proje Haberi", "6/8"),
        ("urun-tanitimi", "Makina Market - Ürün Tanıtımı", "7/8"),
        ("yeni-urun", "Makina Market - Yeni Ürün", "8/8")
    ]
    
    for slug, name, step in mm_cats:
        scrape_mm_category(urls, titles, slug, name, step)

    print(f"\n🏁 İşlem Tamamlandı. {CURRENT_YEAR} yılına ait tüm portallar güncellendi!")

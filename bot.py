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

# --- SİTE 3: MAKİNA MARKET ---
def scrape_makina_market_ana(ex_urls, ex_titles):
    print(f"\n🔍 Makina Market ({CURRENT_YEAR}) Taraması Başladı...")
    page = 1
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }

    while True:
        # Tüm alt kategorilerin de düştüğü ana haberler sayfası
        url = f"https://makina-market.com.tr/category/haberler/page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers=headers)
            if r.status_code != 200: 
                break
                
            soup = BeautifulSoup(r.content, "html.parser")
            articles = soup.find_all("article")
            if not articles: break
            
            found_year_in_page = False
            for art in articles:
                # 1. Tarih Tespiti
                date_div = art.find("div", class_="cs-meta-date")
                tarih = date_div.get_text(strip=True) if date_div else ""
                
                # Sadece mevcut yılın haberlerini al (Örn: 2026)
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
                    
                    # 3. Görsel Çekme (data-src ve src kontrolü ile)
                    img_tag = art.find("img")
                    img_src = ""
                    if img_tag:
                        img_src = img_tag.get("src") or img_tag.get("data-src") or img_tag.get("data-lazy-src")
                    
                    final_img = clean_img(img_src, "https://makina-market.com.tr")
                    
                    # 4. Özet Metin
                    excerpt_div = art.find("div", class_="cs-entry__excerpt")
                    metin = excerpt_div.get_text(strip=True) if excerpt_div else ""
                    
                    # 5. Airtable Kayıt (Adı Sadece Makina Market)
                    table.create({
                        "haber_basligi": baslik,
                        "gorsel": [{"url": final_img}] if final_img else [],
                        "haber_metni": metin,
                        "portal": "Makina Market", # Tek bir isim
                        "url": link
                    })
                    print(f"✅ Eklendi: {baslik[:40]}...")
                    
                    ex_urls.add(link.lower())
                    ex_titles.add(baslik.lower())
                
                # Eğer tarih 2025 veya 2024'e düştüyse daha fazla sayfa tarama
                elif any(old_year in tarih for old_year in ["2025", "2024", "2023"]):
                    # Bu sayfanın geri kalanı ve sonraki sayfalar eskidir
                    print(f"   ℹ️ Eski yıla ulaşıldı: {tarih}")
                    return # Fonksiyondan tamamen çık

            # Eğer sayfada hiç 2026 haberi yoksa dur
            if not found_year_in_page:
                break
                
            page += 1
        except Exception as e:
            print(f"⚠️ Makina Market Hatası: {e}")
            break

# --- SİTE 4: FORMEN DERGİSİ ---
def scrape_formen(ex_urls, ex_titles):
    print(f"\n🔍 [4/4] Formen Dergisi ({CURRENT_YEAR}) Taraması Başladı...")
    page = 1
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }

    while True:
        # Formen Dergisi sayfa yapısı
        url = f"https://formendergisi.com/haber/page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers=headers)
            if r.status_code != 200: break
                
            soup = BeautifulSoup(r.content, "html.parser")
            # TagDiv modüllerini buluyoruz
            modules = soup.find_all("div", class_="tdb_module_loop")
            if not modules: break
            
            found_year_in_page = False
            for mod in modules:
                # 1. Tarih Tespiti (datetime="2026-03-05...")
                time_tag = mod.find("time", class_="entry-date")
                dt_str = time_tag.get("datetime", "") if time_tag else ""
                
                if CURRENT_YEAR in dt_str:
                    found_year_in_page = True
                    
                    # 2. Başlık ve Link
                    title_tag = mod.find("h3", class_="entry-title")
                    if not title_tag: continue
                    link_tag = title_tag.find("a")
                    
                    baslik = link_tag.get("title") or link_tag.get_text(strip=True)
                    link = link_tag["href"]
                    
                    if link.lower() in ex_urls or baslik.lower() in ex_titles:
                        continue
                    
                    # 3. Görsel Çekme (Formen'de görsel data-img-url içindedir)
                    img_span = mod.find("span", class_="entry-thumb")
                    img_src = ""
                    if img_span:
                        img_src = img_span.get("data-img-url") or img_span.get("style")
                        # Eğer style içindeyse temizle (background-image: url("..."))
                        if "url(" in img_src:
                            img_src = img_src.split('url("')[1].split('")')[0]
                    
                    final_img = clean_img(img_src, "https://formendergisi.com")
                    
                    # 4. Haber Özeti (Formen'de bazen meta info içinde kısa özet olur)
                    # Eğer modül içinde özet divi yoksa boş bırakıyoruz
                    metin_div = mod.find("div", class_="td-excerpt")
                    metin = metin_div.get_text(strip=True) if metin_div else ""
                    
                    # 5. Airtable Kayıt
                    table.create({
                        "haber_basligi": baslik,
                        "gorsel": [{"url": final_img}] if final_img else [],
                        "haber_metni": metin,
                        "portal": "Formen Dergisi",
                        "url": link
                    })
                    print(f"✅ Formen: {baslik[:40]}...")
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                
                # Eski yıla geçiş kontrolü
                elif any(old in dt_str for old in ["2025", "2024"]):
                    print(f"   ℹ️ Formen: {CURRENT_YEAR} öncesi haberlere ulaşıldı.")
                    return # Fonksiyondan çık

            if not found_year_in_page: break
            page += 1
        except Exception as e:
            print(f"⚠️ Formen Hatası: {e}")
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

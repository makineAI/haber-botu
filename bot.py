import os
import requests
import time
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

def safe_create(fields):
    try:
        table.create(fields)
        print(f"   🚀 Kaydedildi: {fields['haber_basligi'][:50]}...")
        time.sleep(0.3) 
    except Exception as e:
        print(f"   ❌ HATA: {e}")

def clean_img(url, base_url):
    if not url or "data:image" in url: return ""
    try:
        full_url = urljoin(base_url, url).replace("http://", "https://")
        return full_url
    except: return ""

# ==========================================
# 1. FORUM MAKİNA
# ==========================================
def scrape_forum_makina(ex_urls, ex_titles):
    print(f"\n--- [1/10] Forum Makina ---")
    headers = {'User-Agent': 'Mozilla/5.0'}
    for page in range(1, 5):
        url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        try:
            r = requests.get(url, timeout=15, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            items = soup.find_all("li", class_="news")
            for item in items:
                date_text = item.find("div", class_="date").get_text(strip=True) if item.find("div", class_="date") else ""
                if CURRENT_YEAR in date_text:
                    baslik = item.find("div", class_="title").get_text(strip=True)
                    link = urljoin("https://www.forummakina.com.tr", item.find("a")["href"])
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img = clean_img(item.find("img")["src"], url) if item.find("img") else ""
                    metin = item.find("span").get_text(strip=True).replace("devamı", "")
                    safe_create({"haber_basligi": baslik, "gorsel": [{"url": img}] if img else [], "haber_metni": metin, "portal": "Forum Makina", "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: continue

# ==========================================
# 2. LHT
# ==========================================
def scrape_lht(ex_urls, ex_titles):
    print(f"\n--- [2/10] LHT ---")
    for page in range(1, 5):
        url = f"https://www.lht.com.tr/kategori/haber/page/{page}/" if page > 1 else "https://www.lht.com.tr/kategori/haber/"
        try:
            r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(r.content, "html.parser")
            for art in soup.find_all("article"):
                dt = art.find("time").get("datetime", "") if art.find("time") else ""
                if CURRENT_YEAR in dt:
                    title_tag = art.find("h2")
                    baslik = title_tag.get_text(strip=True); link = title_tag.find("a")["href"]
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img = art.find("img")["src"] if art.find("img") else ""
                    metin = art.find("p", class_="post-excerpt").get_text(strip=True) if art.find("p", class_="post-excerpt") else ""
                    safe_create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img, url)}] if img else [], "haber_metni": metin, "portal": "LHT", "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: continue

# ==========================================
# 3. MAKİNA MARKET (Haber Metni Düzenlendi)
# ==========================================
def scrape_makina_market(ex_urls, ex_titles):
    print(f"\n--- [3/10] Makina Market ---")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    for page in range(1, 4):
        url = f"https://makina-market.com.tr/category/haberler/page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            articles = soup.find_all("article")
            for art in articles:
                title_tag = art.find("h2")
                if not title_tag: continue
                link = title_tag.find("a")["href"]
                baslik = title_tag.get_text(strip=True)
                if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                
                # Metni çekmek için:
                metin_tag = art.find("div", class_="cs-entry__excerpt") or art.find("p")
                metin = metin_tag.get_text(strip=True) if metin_tag else ""

                img_tag = art.find("img")
                img_src = img_tag.get("data-src") or img_tag.get("src") if img_tag else ""
                
                safe_create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, url)}] if img_src else [], "haber_metni": metin, "portal": "Makina Market", "url": link})
                ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: continue

# ==========================================
# 4, 5, 6. FORMEN (Resimler ve Metin Düzenlendi)
# ==========================================
def process_formen(base_url, portal_name, ex_urls, ex_titles):
    print(f"\n--- Tarama: {portal_name} ---")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    for page in range(1, 4):
        url = f"{base_url}page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            items = soup.select(".tdb_module_loop, .td_module_wrap, .td-block-span12, .td_module_10")
            for item in items:
                title_tag = item.find("h3") or item.find("h2")
                if not title_tag or not title_tag.find("a"): continue
                link = title_tag.find("a")["href"]
                baslik = title_tag.get_text(strip=True)
                if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                
                # Görsel için daha agresif tarama
                img_tag = item.find("img")
                img_src = ""
                if img_tag:
                    # Formen'in kullandığı tüm varyasyonları dene:
                    img_src = img_tag.get("data-img-url") or img_tag.get("data-src") or img_tag.get("src") or img_tag.get("srcset")
                    if img_src and " " in img_src: img_src = img_src.split(" ")[0] # srcset varsa ilkini al

                metin_tag = item.find("div", class_="td-excerpt") or item.find("div", class_="tdb-excerpt")
                metin = metin_tag.get_text(strip=True) if metin_tag else ""
                
                safe_create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, url)}] if img_src else [], "haber_metni": metin, "portal": portal_name, "url": link})
                ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: continue

# ==========================================
# 7, 8. İSTİF MH (Sıkı Tarih Denetimi)
# ==========================================
def process_istif_mh(base_url, portal_name, ex_urls, ex_titles):
    print(f"\n--- Tarama: {portal_name} ---")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    for page in range(1, 4):
        url = f"{base_url}page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            items = soup.find_all("div", class_="kanews-post-item")
            for item in items:
                title_tag = item.find("h3")
                if not title_tag: continue
                link = title_tag.find("a")["href"]
                baslik = title_tag.get_text(strip=True)
                if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                
                img_tag = item.find("img")
                img_src = img_tag.get("src") or img_tag.get("data-src") if img_tag else ""
                
                # Sadece 2026 olanları almak için kesin kontrol
                # Görsel yolunda veya meta kısmında 2026 yoksa içeri girmeye zorla
                is_valid = False
                if (img_src and "/2026/" in img_src) or (CURRENT_YEAR in item.get_text()):
                    is_valid = True
                
                # Şüpheli durum: İçeri girip tam tarihe bak
                if not is_valid:
                    try:
                        inner_r = requests.get(link, timeout=10, headers=headers)
                        if f"/{CURRENT_YEAR}/" in inner_r.text or f".{CURRENT_YEAR}" in inner_r.text:
                            is_valid = True
                    except: pass

                if is_valid:
                    safe_create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, url)}] if img_src else [], "portal": portal_name, "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                else:
                    print(f"   ⏭️ Eski Haber (2025/Öncesi) Atlandı: {baslik[:30]}")
        except: continue

# ==========================================
# 9. MADEN OCAK 
# ==========================================
def scrape_maden_ocak(ex_urls, ex_titles):
    print(f"\n--- [9/10] Maden Ocak ---")
    headers = {'User-Agent': 'Mozilla/5.0'}
    for page in range(1, 5):
        url = f"https://www.madenveocak.com.tr/kategori/haber/page/{page}/"
        try:
            r = requests.get(url, timeout=15, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            for art in soup.find_all("article"):
                time_tag = art.find("time")
                if time_tag and CURRENT_YEAR in time_tag.get("datetime", ""):
                    title_tag = art.find("h2"); link = title_tag.find("a")["href"]; baslik = title_tag.get_text(strip=True)
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img_tag = art.find("img"); img_src = img_tag.get("src", "") if img_tag else ""
                    metin = art.find("p", class_="post-excerpt").get_text(strip=True) if art.find("p", class_="post-excerpt") else ""
                    safe_create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, url)}] if img_src else [], "haber_metni": metin, "portal": "Maden Ocak Dergisi", "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: continue

# ==========================================
# 10. ŞANTİYE
# ==========================================
def scrape_santiye(ex_urls, ex_titles):
    print(f"\n--- [10/10] Şantiye ---")
    headers = {'User-Agent': 'Mozilla/5.0'}
    for page in range(1, 5):
        url = f"https://www.santiye.com.tr/haberler.html?page={page}"
        try:
            r = requests.get(url, timeout=15, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            for content in soup.find_all("div", class_="post-content"):
                date_tag = content.find("li")
                if date_tag and CURRENT_YEAR in date_tag.get_text():
                    title_tag = content.find("h2"); a_tag = title_tag.find("a"); baslik = a_tag.get_text(strip=True)
                    link = urljoin("https://www.santiye.com.tr", a_tag["href"])
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    row = content.find_parent("div", class_="row"); img_src = row.find("img").get("src", "") if row and row.find("img") else ""
                    metin = content.find("p").get_text(strip=True) if content.find("p") else ""
                    safe_create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, "https://www.santiye.com.tr")}] if img_src else [], "haber_metni": metin, "portal": "Şantiye", "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: continue

# ==========================================
# ANA ÇALIŞTIRICI
# ==========================================
if __name__ == "__main__":
    urls, titles = get_existing_data()
    print(f"📊 Başlıyoruz! Mevcut Kayıt Sayısı: {len(urls)}")
    
    scrape_forum_makina(urls, titles)
    scrape_lht(urls, titles)
    scrape_makina_market(urls, titles)
    process_formen("https://formendergisi.com/haber/", "Formen Dergisi", urls, titles)
    process_formen("https://formendergisi.com/roportaj/", "Formen - Röportaj", urls, titles)
    process_formen("https://formendergisi.com/dunyadan/", "Formen - Dünya", urls, titles)
    process_istif_mh("https://istifmaterialhandling.com/category/haber/", "İstif MH - Haber", urls, titles)
    process_istif_mh("https://istifmaterialhandling.com/category/manset/", "İstif MH - Manşet", urls, titles)
    scrape_maden_ocak(urls, titles)
    scrape_santiye(urls, titles)
    
    print(f"\n🏁 İŞLEM TAMAMLANDI. TOPLAM KAYIT: {len(urls)}")

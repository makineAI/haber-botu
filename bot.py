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
        print(f"   🚀 Airtable'a Eklendi: {fields['haber_basligi'][:50]}...")
        time.sleep(0.3)
    except Exception as e:
        print(f"   ❌ Yazma Hatası: {e}")

def clean_img(url, base_url):
    if not url or "data:image" in url: return ""
    try:
        full_url = urljoin(base_url, url).replace("http://", "https://")
        parts = full_url.split("/")
        file_part = quote(parts[-1])
        return "/".join(parts[:-1]) + "/" + file_part
    except: return ""

# ==========================================
# İSTİF MH - ÖZEL (İçeri Girip Tarih Kontrolü Yapar)
# ==========================================
def process_istif_mh(base_url, portal_name, ex_urls, ex_titles):
    print(f"\n🔍 [İSTİF MH] {portal_name} Taraması Başladı...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for page in range(1, 4): # İlk 3 sayfayı tara
        url = f"{base_url}page/{page}/" if page > 1 else base_url
        try:
            r = requests.get(url, timeout=20, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            items = soup.find_all("div", class_="kanews-post-item")
            
            for item in items:
                title_tag = item.find("h3", class_="kanews-post-headline")
                if not title_tag: continue
                
                link = title_tag.find("a")["href"]
                baslik = title_tag.get_text(strip=True)
                
                if link.lower() in ex_urls or baslik.lower() in ex_titles:
                    continue

                # HABERİN İÇİNE GİRİP NET TARİHE BAKALIM
                is_valid_date = False
                try:
                    time.sleep(0.2) # Siteyi yormayalım
                    inner_r = requests.get(link, timeout=10, headers=headers)
                    inner_soup = BeautifulSoup(inner_r.content, "html.parser")
                    
                    # 1. Öncelik: meta etiketleri
                    meta_date = inner_soup.find("meta", property="article:published_time")
                    # 2. Öncelik: time etiketi
                    time_tag = inner_soup.find("time")
                    # 3. Öncelik: kanews-post-meta içindeki metin
                    meta_div = inner_soup.find("div", class_="kanews-post-meta")
                    
                    date_content = ""
                    if meta_date: date_content = meta_date.get("content", "")
                    elif time_tag: date_content = time_tag.get("datetime", "") or time_tag.get_text()
                    elif meta_div: date_content = meta_div.get_text()

                    if CURRENT_YEAR in date_content:
                        is_valid_date = True
                    else:
                        print(f"   ⏭️ Eski Haber (2025 veya altı) Atlandı: {baslik[:30]}")
                except:
                    is_valid_date = False # Hata olursa risk alma

                if is_valid_date:
                    img_tag = item.find("img")
                    img_src = img_tag.get("data-src") or img_tag.get("src") if img_tag else ""
                    safe_create({
                        "haber_basligi": baslik,
                        "gorsel": [{"url": clean_img(img_src, url)}] if img_src else [],
                        "haber_metni": "",
                        "portal": portal_name,
                        "url": link
                    })
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: continue

# ==========================================
# FORMEN VE DİĞERLERİ - GÜNCEL SEÇİCİLER
# ==========================================
def process_formen_fix(base_url, portal_name, ex_urls, ex_titles):
    print(f"\n🔍 [FORMEN] {portal_name} Taraması...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    for page in range(1, 4):
        url = f"{base_url}page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            # Hem tdb_module_loop hem de td_module_wrap kısımlarını tara
            items = soup.select(".tdb_module_loop, .td_module_wrap, .td-block-span12")
            for item in items:
                title_tag = item.find("h3")
                if not title_tag or not title_tag.find("a"): continue
                
                link = title_tag.find("a")["href"]
                baslik = title_tag.find("a").get_text(strip=True)
                
                if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                
                # Tarih kontrolü
                time_tag = item.find("time")
                if time_tag and CURRENT_YEAR in (time_tag.get("datetime", "") or time_tag.get_text()):
                    img_src = ""
                    img_tag = item.find("img")
                    if img_tag: img_src = img_tag.get("data-img-url") or img_tag.get("src") or img_tag.get("data-src")
                    
                    safe_create({
                        "haber_basligi": baslik,
                        "gorsel": [{"url": clean_img(img_src, url)}] if img_src else [],
                        "haber_metni": "",
                        "portal": portal_name,
                        "url": link
                    })
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: continue

def scrape_makina_market_fix(ex_urls, ex_titles):
    print(f"\n🔍 [MAKİNA MARKET] Taraması...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    for page in range(1, 4):
        url = f"https://makina-market.com.tr/category/haberler/page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            articles = soup.find_all("article")
            for art in articles:
                date_tag = art.select_one(".cs-meta-date, time")
                if date_tag and CURRENT_YEAR in date_tag.get_text():
                    title_tag = art.find("h2")
                    link = title_tag.find("a")["href"]
                    baslik = title_tag.get_text(strip=True)
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    
                    img_tag = art.find("img")
                    img_src = img_tag.get("data-src") or img_tag.get("src") if img_tag else ""
                    safe_create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, url)}] if img_src else [], "haber_metni": "", "portal": "Makina Market", "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: continue

# --- DİĞER FONKSİYONLAR (LHT, ŞANTİYE VB.) BİR ÖNCEKİ KODDAKİ GİBİ ÇALIŞIYOR ---
# (Kısa tutmak için ana akışı buraya ekliyorum)

if __name__ == "__main__":
    urls, titles = get_existing_data()
    
    # İstif MH İçin Yeni Metot
    process_istif_mh("https://istifmaterialhandling.com/category/haber/", "İstif MH - Haber", urls, titles)
    process_istif_mh("https://istifmaterialhandling.com/category/manset/", "İstif MH - Manşet", urls, titles)
    
    # Formen İçin Yeni Metot
    process_formen_fix("https://formendergisi.com/haber/", "Formen Dergisi", urls, titles)
    process_formen_fix("https://formendergisi.com/roportaj/", "Formen - Röportaj", urls, titles)
    
    # Makina Market Fix
    scrape_makina_market_fix(urls, titles)
    
    # Buraya diğerlerini (LHT, Maden Ocak, Şantiye) önceki sağlam halleriyle ekleyebilirsin.
    print(f"\n🏁 İşlem Tamamlandı.")

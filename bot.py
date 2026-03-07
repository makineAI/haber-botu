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
    print("🔍 Airtable verileri kontrol ediliyor...")
    ex_urls, ex_titles = set(), set()
    try:
        records = table.all()
        for r in records:
            f = r.get('fields', {})
            u = f.get('url', '').strip().lower()
            t = f.get('haber_basligi', '').strip().lower()
            if u: ex_urls.add(u)
            if t: ex_titles.add(t)
        print(f"✅ Airtable'da {len(ex_urls)} mevcut kayıt bulundu.")
        return ex_urls, ex_titles
    except Exception as e:
        print(f"❌ Airtable Veri Çekme Hatası: {e}")
        return set(), set()

def clean_img(url, base_url):
    if not url: return ""
    try:
        full_url = urljoin(base_url, url).replace("http://", "https://")
        parts = full_url.split("/")
        file_part = quote(parts[-1])
        return "/".join(parts[:-1]) + "/" + file_part
    except: return ""

def safe_create(fields):
    """Airtable'a veri yazarken hata kontrolü yapar ve hız sınırına (rate limit) takılmaz."""
    try:
        table.create(fields)
        print(f"   🚀 Airtable'a Yazıldı: {fields['haber_basligi'][:40]}...")
        time.sleep(0.3) # Saniyede 5 istek sınırını aşmamak için
    except Exception as e:
        print(f"   ❌ AIRTABLE YAZMA HATASI: {e}")

# ==========================================
# 1. FORUM MAKİNA
# ==========================================
def scrape_forum_makina(ex_urls, ex_titles):
    print(f"\n--- [1/10] Forum Makina ---")
    headers = {'User-Agent': 'Mozilla/5.0'}
    for page in range(1, 4):
        url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        try:
            r = requests.get(url, timeout=15, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            items = soup.find_all("li", class_="news")
            for item in items:
                date_text = item.find("div", class_="date").get_text(strip=True) if item.find("div", class_="date") else ""
                if CURRENT_YEAR in date_text:
                    baslik = item.find("div", class_="title").get_text(strip=True) if item.find("div", class_="title") else ""
                    link = urljoin("https://www.forummakina.com.tr", item.find("a")["href"])
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img = clean_img(item.find("img")["src"], url) if item.find("img") else ""
                    metin = item.find("span").get_text(strip=True).replace("devamı", "") if item.find("span") else ""
                    safe_create({"haber_basligi": baslik, "gorsel": [{"url": img}] if img else [], "haber_metni": metin, "portal": "Forum Makina", "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except Exception as e: print(f"Hata: {e}")

# ==========================================
# 2. LHT
# ==========================================
def scrape_lht(ex_urls, ex_titles):
    print(f"\n--- [2/10] LHT ---")
    for page in range(1, 4):
        url = f"https://www.lht.com.tr/kategori/haber/page/{page}/" if page > 1 else "https://www.lht.com.tr/kategori/haber/"
        try:
            r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(r.content, "html.parser")
            articles = soup.find_all("article")
            for art in articles:
                dt = art.find("time").get("datetime", "") if art.find("time") else ""
                if CURRENT_YEAR in dt:
                    title_tag = art.find("h2")
                    baslik = title_tag.get_text(strip=True); link = title_tag.find("a")["href"]
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img = art.find("img")["src"] if art.find("img") else ""
                    metin = art.find("p", class_="post-excerpt").get_text(strip=True) if art.find("p", class_="post-excerpt") else ""
                    safe_create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img, url)}] if img else [], "haber_metni": metin, "portal": "LHT", "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: pass

# ==========================================
# 3. MAKİNA MARKET
# ==========================================
def scrape_makina_market(ex_urls, ex_titles):
    print(f"\n--- [3/10] Makina Market ---")
    headers = {'User-Agent': 'Mozilla/5.0'}
    for page in range(1, 4):
        url = f"https://makina-market.com.tr/category/haberler/page/{page}/" if page > 1 else "https://makina-market.com.tr/category/haberler/"
        try:
            r = requests.get(url, timeout=15, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            articles = soup.find_all("article")
            for art in articles:
                tarih = art.find("div", class_="cs-meta-date").get_text(strip=True) if art.find("div", class_="cs-meta-date") else ""
                if CURRENT_YEAR in tarih:
                    title_tag = art.find("h2"); baslik = title_tag.get_text(strip=True); link = title_tag.find("a")["href"]
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img_tag = art.find("img"); img_src = img_tag.get("src") or img_tag.get("data-src") if img_tag else ""
                    metin = art.find("div", class_="cs-entry__excerpt").get_text(strip=True) if art.find("div", class_="cs-entry__excerpt") else ""
                    safe_create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, url)}] if img_src else [], "haber_metni": metin, "portal": "Makina Market", "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: pass

# ==========================================
# 4, 5, 6. FORMEN (ORTAK FONKSİYON)
# ==========================================
def process_formen(base_url, portal_name, ex_urls, ex_titles):
    print(f"\n--- Tarama: {portal_name} ---")
    headers = {'User-Agent': 'Mozilla/5.0'}
    for page in range(1, 4):
        url = f"{base_url}page/{page}/" if page > 1 else base_url
        try:
            r = requests.get(url, timeout=15, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            modules = soup.find_all("div", class_="tdb_module_loop")
            for mod in modules:
                time_tag = mod.find("time"); dt = time_tag.get("datetime", "") if time_tag else ""
                if CURRENT_YEAR in dt:
                    title_tag = mod.find("h3", class_="entry-title")
                    if not title_tag: continue
                    link = title_tag.find("a")["href"]; baslik = title_tag.find("a").get_text(strip=True)
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img_span = mod.find("span", class_="entry-thumb"); img_src = img_span.get("data-img-url") if img_span else ""
                    safe_create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, url)}] if img_src else [], "haber_metni": "", "portal": portal_name, "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: pass

# ==========================================
# 7, 8. İSTİF MH (TARİH FİLTRELİ)
# ==========================================
def process_istif(base_url, portal_name, ex_urls, ex_titles):
    print(f"\n--- Tarama: {portal_name} ---")
    headers = {'User-Agent': 'Mozilla/5.0'}
    for page in range(1, 3):
        url = f"{base_url}page/{page}/" if page > 1 else base_url
        try:
            r = requests.get(url, timeout=15, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            items = soup.find_all("div", class_="kanews-post-item")
            for item in items:
                title_tag = item.find("h3", class_="kanews-post-headline"); link = title_tag.find("a")["href"]; baslik = title_tag.get_text(strip=True)
                if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                
                is_2026 = False
                try:
                    rd = requests.get(link, timeout=10, headers=headers)
                    ds = BeautifulSoup(rd.content, "html.parser")
                    meta = ds.find("meta", property="article:published_time")
                    if meta and CURRENT_YEAR in meta.get("content", ""): is_2026 = True
                    else:
                        tm = ds.find("time")
                        if tm and CURRENT_YEAR in (tm.get("datetime", "") or tm.get_text()): is_2026 = True
                except: pass

                if is_2026:
                    img_tag = item.find("img"); img_src = clean_img(img_tag.get("src") or img_tag.get("data-src"), url) if img_tag else ""
                    safe_create({"haber_basligi": baslik, "gorsel": [{"url": img_src}] if img_src else [], "haber_metni": "", "portal": portal_name, "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: pass

# ==========================================
# 9. MADEN OCAK
# ==========================================
def scrape_maden_ocak(ex_urls, ex_titles):
    print(f"\n--- [9/10] Maden Ocak ---")
    headers = {'User-Agent': 'Mozilla/5.0'}
    for page in range(1, 4):
        url = f"https://www.madenveocak.com.tr/kategori/haber/page/{page}/" if page > 1 else "https://www.madenveocak.com.tr/kategori/haber/"
        try:
            r = requests.get(url, timeout=15, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            articles = soup.find_all("article")
            for art in articles:
                time_tag = art.find("time"); dt = time_tag.get("datetime", "") if time_tag else ""
                if CURRENT_YEAR in dt:
                    title_tag = art.find("h2", class_="entry-title"); link = title_tag.find("a")["href"]; baslik = title_tag.find("a").get_text(strip=True)
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img_tag = art.find("img"); img_src = img_tag.get("src", "") if img_tag else ""
                    metin = art.find("p", class_="post-excerpt").get_text(strip=True) if art.find("p", class_="post-excerpt") else ""
                    safe_create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, url)}] if img_src else [], "haber_metni": metin, "portal": "Maden Ocak Dergisi", "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: pass

# ==========================================
# 10. ŞANTİYE
# ==========================================
def scrape_santiye(ex_urls, ex_titles):
    print(f"\n--- [10/10] Şantiye ---")
    headers = {'User-Agent': 'Mozilla/5.0'}
    for page in range(1, 4):
        url = f"https://www.santiye.com.tr/haberler.html?page={page}" if page > 1 else "https://www.santiye.com.tr/haberler.html"
        try:
            r = requests.get(url, timeout=15, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            contents = soup.find_all("div", class_="post-content")
            for content in contents:
                date_tag = content.find("li"); dt = date_tag.get_text(strip=True) if date_tag else ""
                if CURRENT_YEAR in dt:
                    title_tag = content.find("h2"); a_tag = title_tag.find("a"); baslik = a_tag.get_text(strip=True)
                    link = urljoin("https://www.santiye.com.tr", a_tag["href"])
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    row = content.find_parent("div", class_="row"); img_src = row.find("img").get("src", "") if row and row.find("img") else ""
                    metin = content.find("p").get_text(strip=True).replace("[..]", "") if content.find("p") else ""
                    safe_create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, "https://www.santiye.com.tr")}] if img_src else [], "haber_metni": metin, "portal": "Şantiye", "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: pass

if __name__ == "__main__":
    urls, titles = get_existing_data()
    scrape_forum_makina(urls, titles)
    scrape_lht(urls, titles)
    scrape_makina_market(urls, titles)
    process_formen("https://formendergisi.com/haber/", "Formen Dergisi", urls, titles)
    process_formen("https://formendergisi.com/roportaj/", "Formen - Röportaj", urls, titles)
    process_formen("https://formendergisi.com/dunyadan/", "Formen - Dünya", urls, titles)
    process_istif("https://istifmaterialhandling.com/category/haber/", "İstif MH - Haber", urls, titles)
    process_istif("https://istifmaterialhandling.com/category/manset/", "İstif MH - Manşet", urls, titles)
    scrape_maden_ocak(urls, titles)
    scrape_santiye(urls, titles)
    print(f"\n🏁 İşlem bitti.")

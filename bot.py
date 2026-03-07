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

# ==========================================
# 1. FORUM MAKİNA
# ==========================================
def scrape_forum_makina(ex_urls, ex_titles):
    print(f"\n🔍 [1/10] Forum Makina ({CURRENT_YEAR}) Taraması...")
    page = 1
    headers = {'User-Agent': 'Mozilla/5.0'}
    while True:
        url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        try:
            r = requests.get(url, timeout=20, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            items = soup.find_all("li", class_="news")
            if not items: break
            found = False
            for item in items:
                date_text = item.find("div", class_="date").get_text(strip=True) if item.find("div", class_="date") else ""
                if CURRENT_YEAR in date_text:
                    found = True
                    baslik = item.find("div", class_="title").get_text(strip=True) if item.find("div", class_="title") else ""
                    link = urljoin("https://www.forummakina.com.tr", item.find("a")["href"])
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img = clean_img(item.find("img")["src"], url) if item.find("img") else ""
                    metin = item.find("span").get_text(strip=True).replace("devamı", "") if item.find("span") else ""
                    table.create({"haber_basligi": baslik, "gorsel": [{"url": img}] if img else [], "haber_metni": metin, "portal": "Forum Makina", "url": link})
                    print(f"✅ Forum Makina: {baslik[:30]}")
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
            if not found: break
            page += 1
        except: break

# ==========================================
# 2. LHT
# ==========================================
def scrape_lht(ex_urls, ex_titles):
    print(f"\n🔍 [2/10] LHT ({CURRENT_YEAR}) Taraması...")
    page = 1
    while True:
        url = f"https://www.lht.com.tr/kategori/haber/page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code != 200: break
            soup = BeautifulSoup(r.content, "html.parser")
            articles = soup.find_all("article")
            if not articles: break
            found = False
            for art in articles:
                dt = art.find("time").get("datetime", "") if art.find("time") else ""
                if CURRENT_YEAR in dt:
                    found = True
                    title_tag = art.find("h2")
                    baslik = title_tag.get_text(strip=True)
                    link = title_tag.find("a")["href"]
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img = art.find("img")["src"] if art.find("img") else ""
                    metin = art.find("p", class_="post-excerpt").get_text(strip=True) if art.find("p", class_="post-excerpt") else ""
                    table.create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img, url)}] if img else [], "haber_metni": metin, "portal": "LHT", "url": link})
                    print(f"✅ LHT: {baslik[:30]}")
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
            if not found: break
            page += 1
        except: break

# ==========================================
# 3. MAKİNA MARKET
# ==========================================
def scrape_makina_market_ana(ex_urls, ex_titles):
    print(f"\n🔍 [3/10] Makina Market ({CURRENT_YEAR}) Taraması...")
    page = 1
    headers = {'User-Agent': 'Mozilla/5.0'}
    while True:
        url = f"https://makina-market.com.tr/category/haberler/page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers=headers)
            if r.status_code != 200: break
            soup = BeautifulSoup(r.content, "html.parser")
            articles = soup.find_all("article")
            if not articles: break
            found = False
            for art in articles:
                tarih = art.find("div", class_="cs-meta-date").get_text(strip=True) if art.find("div", class_="cs-meta-date") else ""
                if CURRENT_YEAR in tarih:
                    found = True
                    title_tag = art.find("h2")
                    baslik = title_tag.get_text(strip=True)
                    link = title_tag.find("a")["href"]
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img_tag = art.find("img")
                    img_src = img_tag.get("src") or img_tag.get("data-src") if img_tag else ""
                    metin = art.find("div", class_="cs-entry__excerpt").get_text(strip=True) if art.find("div", class_="cs-entry__excerpt") else ""
                    table.create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, url)}] if img_src else [], "haber_metni": metin, "portal": "Makina Market", "url": link})
                    print(f"✅ Makina Market: {baslik[:30]}")
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                elif any(old in tarih for old in ["2025", "2024"]): return
            if not found: break
            page += 1
        except: break

# ==========================================
# 4, 5, 6. FORMEN (ORTAK FONKSİYON)
# ==========================================
def process_formen_category(base_url, portal_name, ex_urls, ex_titles):
    page = 1
    headers = {'User-Agent': 'Mozilla/5.0'}
    while True:
        url = f"{base_url}page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers=headers)
            if r.status_code != 200: break
            soup = BeautifulSoup(r.content, "html.parser")
            modules = soup.find_all("div", class_="tdb_module_loop")
            if not modules: break
            found = False
            for mod in modules:
                time_tag = mod.find("time")
                dt = time_tag.get("datetime", "") if time_tag else ""
                if CURRENT_YEAR in dt:
                    found = True
                    title_tag = mod.find("h3", class_="entry-title")
                    if not title_tag: continue
                    link = title_tag.find("a")["href"]
                    baslik = title_tag.find("a").get_text(strip=True)
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img_span = mod.find("span", class_="entry-thumb")
                    img_src = img_span.get("data-img-url") if img_span else ""
                    
                    # Ön metin istenmediği için boş ("") bırakıyoruz
                    table.create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, url)}] if img_src else [], "haber_metni": "", "portal": portal_name, "url": link})
                    print(f"✅ {portal_name}: {baslik[:30]}")
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                elif any(old in dt for old in ["2025", "2024"]): return
            if not found: break
            page += 1
        except: break

# ==========================================
# 7, 8. İSTİF MH (ORTAK FONKSİYON)
# ==========================================
def process_istif_category(base_url, portal_name, ex_urls, ex_titles):
    page = 1
    headers = {'User-Agent': 'Mozilla/5.0'}
    while True:
        url = f"{base_url}page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers=headers)
            if r.status_code != 200: break
            soup = BeautifulSoup(r.content, "html.parser")
            items = soup.find_all("div", class_="kanews-post-item")
            if not items: break
            
            new_added_on_page = 0
            for item in items:
                title_tag = item.find("h3", class_="kanews-post-headline")
                if not title_tag: continue
                link = title_tag.find("a")["href"]
                baslik = title_tag.get_text(strip=True)
                
                if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                
                # Derin Tarama: 2026 Filtresi
                try:
                    r_det = requests.get(link, timeout=10, headers=headers)
                    det_text = BeautifulSoup(r_det.content, "html.parser").get_text()
                    if any(old in det_text for old in ["2025", "2024"]) and CURRENT_YEAR not in det_text:
                        continue
                except: pass

                img_tag = item.find("img")
                img_src = clean_img(img_tag.get("src") or img_tag.get("data-src"), url) if img_tag else ""
                
                table.create({
                    "haber_basligi": baslik,
                    "gorsel": [{"url": img_src}] if img_src else [],
                    "haber_metni": "", 
                    "portal": portal_name,
                    "url": link
                })
                print(f"✅ {portal_name}: {baslik[:30]}")
                ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                new_added_on_page += 1

            if page >= 5: break 
            page += 1
        except: break

# ==========================================
# 9. MADEN OCAK DERGİSİ
# ==========================================
def scrape_maden_ocak(ex_urls, ex_titles):
    print(f"\n🔍 [9/10] Maden Ocak Dergisi ({CURRENT_YEAR}) Taraması...")
    page = 1
    headers = {'User-Agent': 'Mozilla/5.0'}
    while True:
        url = f"https://www.madenveocak.com.tr/kategori/haber/page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers=headers)
            if r.status_code != 200: break
            soup = BeautifulSoup(r.content, "html.parser")
            articles = soup.find_all("article")
            if not articles: break
            found = False
            for art in articles:
                time_tag = art.find("time")
                dt = time_tag.get("datetime", "") if time_tag else ""
                if CURRENT_YEAR in dt:
                    found = True
                    title_tag = art.find("h2", class_="entry-title")
                    if not title_tag: continue
                    link = title_tag.find("a")["href"]
                    baslik = title_tag.find("a").get_text(strip=True)
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    
                    img_tag = art.find("img")
                    img_src = img_tag.get("src", "") if img_tag else ""
                    p_tag = art.find("p", class_="post-excerpt")
                    metin = p_tag.get_text(strip=True) if p_tag else ""
                    
                    table.create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, url)}] if img_src else [], "haber_metni": metin, "portal": "Maden Ocak Dergisi", "url": link})
                    print(f"✅ Maden Ocak: {baslik[:30]}")
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                elif any(old in dt for old in ["2025", "2024"]): return
            if not found: break
            page += 1
        except: break

# ==========================================
# 10. ŞANTİYE
# ==========================================
def scrape_santiye(ex_urls, ex_titles):
    print(f"\n🔍 [10/10] Şantiye ({CURRENT_YEAR}) Taraması...")
    page = 1
    headers = {'User-Agent': 'Mozilla/5.0'}
    while True:
        # Sayfalama yapısı: ?page=1, ?page=2
        url = f"https://www.santiye.com.tr/haberler.html?page={page}" if page > 1 else "https://www.santiye.com.tr/haberler.html"
        try:
            r = requests.get(url, timeout=20, headers=headers)
            if r.status_code != 200: break
            soup = BeautifulSoup(r.content, "html.parser")
            contents = soup.find_all("div", class_="post-content")
            if not contents: break
            found = False
            for content in contents:
                date_tag = content.find("li") # <i class="fa fa-clock-o"></i>06.03.2026 barındırıyor
                dt = date_tag.get_text(strip=True) if date_tag else ""
                
                if CURRENT_YEAR in dt:
                    found = True
                    title_tag = content.find("h2")
                    if not title_tag: continue
                    a_tag = title_tag.find("a")
                    baslik = a_tag.get_text(strip=True)
                    raw_link = a_tag["href"]
                    link = urljoin("https://www.santiye.com.tr", raw_link)
                    
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    
                    # Görseli bir üst div'den (row) yakalıyoruz
                    row = content.find_parent("div", class_="row")
                    img_src = ""
                    if row and row.find("img"):
                        img_src = row.find("img").get("src", "")
                        
                    p_tag = content.find("p")
                    metin = p_tag.get_text(strip=True).replace("[..]", "") if p_tag else ""
                    
                    table.create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, "https://www.santiye.com.tr")}] if img_src else [], "haber_metni": metin, "portal": "Şantiye", "url": link})
                    print(f"✅ Şantiye: {baslik[:30]}")
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                elif any(old in dt for old in ["2025", "2024"]): return
            if not found: break
            page += 1
        except: break


# ==========================================
# ANA ÇALIŞTIRICI (MOTOR)
# ==========================================
if __name__ == "__main__":
    urls, titles = get_existing_data()
    print(f"📊 Tarama Başlıyor... (Airtable'daki Mevcut Kayıt: {len(urls)})")
    
    # 1. Forum Makina
    scrape_forum_makina(urls, titles)
    
    # 2. LHT
    scrape_lht(urls, titles)
    
    # 3. Makina Market
    scrape_makina_market_ana(urls, titles)
    
    # 4, 5, 6. Formen Kategorileri
    print(f"\n🔍 [4/10] Formen Dergisi ({CURRENT_YEAR}) Taraması...")
    process_formen_category("https://formendergisi.com/haber/", "Formen Dergisi", urls, titles)
    print(f"\n🔍 [5/10] Formen - Röportaj ({CURRENT_YEAR}) Taraması...")
    process_formen_category("https://formendergisi.com/roportaj/", "Formen - Röportaj", urls, titles)
    print(f"\n🔍 [6/10] Formen - Dünya ({CURRENT_YEAR}) Taraması...")
    process_formen_category("https://formendergisi.com/dunyadan/", "Formen - Dünya", urls, titles)
    
    # 7, 8. İstif MH Kategorileri
    print(f"\n🔍 [7/10] İstif MH - Haber Taraması Başladı...")
    process_istif_category("https://istifmaterialhandling.com/category/haber/", "İstif MH - Haber", urls, titles)
    print(f"\n🔍 [8/10] İstif MH - Manşet Taraması Başladı...")
    process_istif_category("https://istifmaterialhandling.com/category/manset/", "İstif MH - Manşet", urls, titles)
    
    # 9. Maden Ocak
    scrape_maden_ocak(urls, titles)
    
    # 10. Şantiye
    scrape_santiye(urls, titles)

    print(f"\n🏁 DEV İŞLEM TAMAMLANDI! Tüm 10 Kol Başarıyla Taranarak Airtable'a Aktarıldı.")

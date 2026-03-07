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

# --- 1. FORUM MAKİNA ---
def scrape_forum_makina(ex_urls, ex_titles):
    print(f"\n🔍 [1/4] Forum Makina ({CURRENT_YEAR}) Taraması...")
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

# --- 2. LHT ---
def scrape_lht(ex_urls, ex_titles):
    print(f"\n🔍 [2/4] LHT ({CURRENT_YEAR}) Taraması...")
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

# --- 3. MAKİNA MARKET ---
def scrape_makina_market_ana(ex_urls, ex_titles):
    print(f"\n🔍 [3/4] Makina Market ({CURRENT_YEAR}) Taraması...")
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

# --- 4. FORMEN DERGİSİ ---
def scrape_formen(ex_urls, ex_titles):
    print(f"\n🔍 [4/4] Formen Dergisi ({CURRENT_YEAR}) Taraması...")
    page = 1
    headers = {'User-Agent': 'Mozilla/5.0'}
    while True:
        url = f"https://formendergisi.com/haber/page/{page}/"
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
                    link = title_tag.find("a")["href"]
                    baslik = title_tag.find("a").get_text(strip=True)
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img_span = mod.find("span", class_="entry-thumb")
                    img_src = img_span.get("data-img-url") if img_span else ""
                    table.create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, url)}] if img_src else [], "haber_metni": "", "portal": "Formen Dergisi", "url": link})
                    print(f"✅ Formen: {baslik[:30]}")
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                elif any(old in dt for old in ["2025", "2024"]): return
            if not found: break
            page += 1
        except: break

# --- SİTE 5: İSTİF MH - DETAYDAN TARİH ALAN VERSİYON ---
def scrape_istif_mh(ex_urls, ex_titles):
    print(f"\n🔍 [5/5] İstif MH - Haber Taraması (Derin Tarama) Başladı...")
    page = 1
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    while True:
        url = f"https://istifmaterialhandling.com/category/haber/page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers=headers)
            if r.status_code != 200: break
                
            soup = BeautifulSoup(r.content, "html.parser")
            items = soup.find_all("div", class_="kanews-post-item")
            if not items: break
            
            new_added = 0
            for item in items:
                title_tag = item.find("h3", class_="kanews-post-headline")
                if not title_tag: continue
                link = title_tag.find("a")["href"]
                baslik = title_tag.get_text(strip=True)
                
                # Mükerrer Kontrolü (Airtable'da varsa hiç içeri girme)
                if link.lower() in ex_urls or baslik.lower() in ex_titles:
                    continue
                
                # --- DERİN TARAMA: Haberin içine girip net tarihi alalım ---
                print(f"   ∟ Detay okunuyor: {baslik[:30]}...")
                try:
                    r_detail = requests.get(link, timeout=10, headers=headers)
                    soup_detail = BeautifulSoup(r_detail.content, "html.parser")
                    
                    # Detay sayfasındaki tarih divini/spanını bul (Genelde meta alanında olur)
                    # Not: Sitenin detay yapısında tarih genelde 'kanews-post-date' içindedir
                    detail_date_tag = soup_detail.find("span", class_="kanews-post-date") or \
                                      soup_detail.find("time")
                    net_tarih = detail_date_tag.get_text(strip=True) if detail_date_tag else "Tarih Belirsiz"
                except:
                    net_tarih = "Okunamadı"

                # Sadece 2026 haberlerini alalım (veya güncel olanları)
                if CURRENT_YEAR not in net_tarih:
                    # Eğer çok eski bir yıla geldiysek (2025, 2024 vb.) durabiliriz
                    if any(year in net_tarih for year in ["2025", "2024"]):
                        print(f"   ℹ️ Eski yıla ulaşıldı ({net_tarih}), tarama duruyor.")
                        return 

                img_tag = item.find("img")
                img_src = clean_img(img_tag.get("src") or img_tag.get("data-src"), url) if img_tag else ""
                
                # Airtable Kayıt
                table.create({
                    "haber_basligi": baslik,
                    "gorsel": [{"url": img_src}] if img_src else [],
                    "haber_metni": f"Net Yayın Tarihi: {net_tarih}",
                    "portal": "İstif MH - Haber",
                    "url": link
                })
                print(f"✅ Eklendi: {baslik[:30]} | Tarih: {net_tarih}")
                ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                new_added += 1

            if new_added == 0: break
            page += 1
        except Exception as e:
            print(f"⚠️ İstif MH Hatası: {e}")
            break

if __name__ == "__main__":
    urls, titles = get_existing_data()
    print(f"📊 Airtable'da şu an toplam {len(urls)} adet kayıtlı link var.")
    
    # 1. Forum Makina
    scrape_forum_makina(urls, titles)
    # 2. LHT
    scrape_lht(urls, titles)
    # 3. Makina Market
    scrape_makina_market_ana(urls, titles)
    # 4. Formen Dergisi
    scrape_formen(urls, titles)
    # 5. İstif MH (Eğer kodunu eklediysen bunu da buraya yaz)
    # scrape_istif_mh(urls, titles) 

    print(f"\n🏁 Tarama bitti. Eğer yukarıda ✅ görmediysen, tüm haberler zaten Airtable'da kayıtlı demektir.")

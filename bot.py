import os
import requests
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from urllib.parse import urljoin
from datetime import datetime

load_dotenv()
CURRENT_YEAR = str(datetime.now().year)

# ==========================================
# AYARLAR (GEMINI KAPALI - MALİYET SIFIR)
# ==========================================
BASEROW_TOKEN = os.environ.get('BASEROW_TOKEN')
BASEROW_TABLE_ID = "1197624"

if not BASEROW_TOKEN:
    print("❌ HATA: Baserow şifresi bulunamadı!")
    exit()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
}

def format_date(date_str):
    if not date_str: return datetime.now().strftime("%Y-%m-%d")
    if len(date_str) >= 10 and date_str[4] == '-' and date_str[7] == '-': return date_str[:10]
    aylar = {"Ocak": "01", "Şubat": "02", "Mart": "03", "Nisan": "04", "Mayıs": "05", "Haziran": "06", 
             "Temmuz": "07", "Ağustos": "08", "Eylül": "09", "Ekim": "10", "Kasım": "11", "Aralık": "12",
             "Oca": "01", "Şub": "02", "Mar": "03", "Nis": "04", "May": "05", "Haz": "06", 
             "Tem": "07", "Ağu": "08", "Eyl": "09", "Eki": "10", "Kas": "11", "Ara": "12"}
    try:
        match_year = re.search(r'202\d', date_str)
        year = match_year.group(0) if match_year else str(datetime.now().year)
        match_day = re.search(r'\b(0?[1-9]|[12][0-9]|3[01])\b', date_str)
        day = match_day.group(0).zfill(2) if match_day else "01"
        month = "01"
        for tr, num in aylar.items():
            if tr.lower() in date_str.lower(): month = num; break
        if month == "01":
            num_match = re.search(r'\b(0?[1-9]|[12][0-9]|3[01])[./-](0?[1-9]|1[012])[./-](202\d)\b', date_str)
            if num_match: return f"{num_match.group(3)}-{num_match.group(2).zfill(2)}-{num_match.group(1).zfill(2)}"
        return f"{year}-{month}-{day}"
    except: return datetime.now().strftime("%Y-%m-%d")

# ==========================================
# EVRENSEL GÖRSEL AVCISI
# ==========================================
def get_universal_img(soup_obj, base_url):
    if not soup_obj: return ""
    
    # 1. Taktik: data-img-url (Formen)
    thumb = soup_obj.find(attrs={"data-img-url": True})
    if thumb and thumb.get("data-img-url"):
        return thumb.get("data-img-url").split('?')[0]
        
    # 2. Taktik: Normal img etiketleri (Şantiye, Forum Makina)
    imgs = soup_obj.find_all("img")
    for img in imgs:
        src = img.get("src") or img.get("data-src")
        if src and "data:image" not in src and "logo" not in src.lower():
            src = src.split('?')[0] # Şantiyenin ?v=1.0 kısmını siler
            return src if src.startswith('http') else urljoin(base_url, src)
            
    # 3. Taktik: CSS Background-image arama
    styled_elements = soup_obj.find_all(attrs={"style": True})
    for el in styled_elements:
        style_text = el.get("style", "")
        if "background-image" in style_text or "background" in style_text:
            match = re.search(r'url\([\'"]?(.*?)[\'"]?\)', style_text)
            if match:
                src = match.group(1).split('?')[0]
                return src if src.startswith('http') else urljoin(base_url, src)
                
    return ""

def get_existing_data():
    ex_urls, ex_titles = set(), set()
    url = f"https://api.baserow.io/api/database/rows/table/{BASEROW_TABLE_ID}/?user_field_names=true&size=200"
    headers = {"Authorization": f"Token {BASEROW_TOKEN}"}
    print("🔄 Baserow'dan eski kayıtlar kontrol ediliyor...")
    try:
        while url:
            res = requests.get(url, headers=headers, timeout=20).json()
            for r in res.get('results', []):
                if r.get('url'): ex_urls.add(r.get('url').strip().lower())
                if r.get('haber_basligi'): ex_titles.add(r.get('haber_basligi').strip().lower())
            url = res.get('next')
        return ex_urls, ex_titles
    except Exception: return set(), set()

def clean_html(soup):
    garbage = ['.share', '.twit', 'script', 'style', '.pk-share-buttons-wrap', '#comments', '.cs-entry__subscribe', '#related-articles', '.td-post-sharing', '.tdb_single_tags', '.tdb_single_comments', '#newsletter']
    for sel in garbage:
        for tag in soup.select(sel): tag.decompose()
    return soup

def extract_clean_text(html_content, container_selector, is_santiye=False):
    soup = BeautifulSoup(html_content, "html.parser")
    soup = clean_html(soup)
    content = soup.select_one(container_selector)
    if not content: content = soup.find('article') or soup.find('div', class_=re.compile(r'content|post|entry|detay|news-detail|text', re.I))
    if not content: return ""
        
    if is_santiye:
        hr_tag = content.find('hr')
        if hr_tag:
            for sibling in hr_tag.find_next_siblings(): sibling.decompose()
            hr_tag.decompose()
            
    paragraphs = [p.get_text(strip=True) for p in content.find_all('p') if p.get_text(strip=True)]
    return "\n".join(paragraphs) if paragraphs else content.get_text(separator="\n", strip=True)

def upload_image_to_baserow(img_url):
    if not img_url: return None
    url = "https://api.baserow.io/api/user-files/upload-via-url/"
    headers = {"Authorization": f"Token {BASEROW_TOKEN}", "Content-Type": "application/json"}
    try:
        res = requests.post(url, headers=headers, json={"url": img_url}, timeout=20)
        if res.status_code == 200: return res.json().get("name")
    except: pass
    return None

def safe_create(fields):
    img_url = fields.get("gorsel", "")
    print(f"   📸 Görsel Linki: {img_url if img_url else 'BULUNAMADI'}")
    
    uploaded_name = upload_image_to_baserow(img_url) if img_url else None
    fields["gorsel"] = [{"name": uploaded_name}] if uploaded_name else []

    # YAPAY ZEKA KAPALI: Sadece yer tutucu metin yazıyoruz.
    fields["haber_ozeti"] = "Analiz Bekleniyor"
    fields["mai_analizi"] = "Analiz Bekleniyor"

    url = f"https://api.baserow.io/api/database/rows/table/{BASEROW_TABLE_ID}/?user_field_names=true"
    headers = {"Authorization": f"Token {BASEROW_TOKEN}", "Content-Type": "application/json"}
    try:
        res = requests.post(url, headers=headers, json=fields, timeout=20)
        if res.status_code == 200: print(f"   ✅ Kayıt Başarılı: {fields['haber_basligi'][:40]}...")
        else: print(f"   ❌ Kayıt Hatası: {res.text}")
    except Exception as e: print(f"   ❌ Bağlantı Hatası: {e}")

# ==========================================
# TARAMA FONKSİYONLARI (KESİN OLARAK SADECE 1 ÖRNEK)
# ==========================================
def scrape_forum_makina(ex_urls, ex_titles):
    print(f"\n--- Tarama: Forum Makina (Maks 1) ---")
    url = "https://www.forummakina.com.tr/tr/haberler?page=1"
    try:
        r = requests.get(url, timeout=15, headers=HEADERS)
        soup = BeautifulSoup(r.content, "html.parser")
        for item in soup.find_all("li", class_="news"):
            date_text = item.find("div", class_="date").get_text(strip=True) if item.find("div", class_="date") else ""
            if CURRENT_YEAR in date_text:
                baslik = item.find("div", class_="title").get_text(strip=True)
                link = urljoin("https://www.forummakina.com.tr", item.find("a")["href"])
                if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                
                list_img = get_universal_img(item, url)
                print(f"   🔎 İşleniyor: {baslik[:30]}...")
                
                inner_r = requests.get(link, timeout=15, headers=HEADERS)
                inner_img = get_universal_img(BeautifulSoup(inner_r.content, "html.parser").select_one('.newsDetail'), url)
                img = inner_img if inner_img else list_img
                
                tam_metin = extract_clean_text(inner_r.content, '.newsDetail')
                safe_create({"haber_basligi": baslik, "gorsel": img, "haber_metni": tam_metin, "yayin_tarihi": format_date(date_text), "portal": "Forum Makina", "url": link})
                ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                return # İLK HABERİ ATAR ATMAZ DURUR
    except Exception as e: print(f"Hata: {e}")

def scrape_newsplus_theme(base_url, portal_name, ex_urls, ex_titles):
    print(f"\n--- Tarama: {portal_name} (Maks 1) ---")
    try:
        r = requests.get(base_url, timeout=15, headers=HEADERS)
        soup = BeautifulSoup(r.content, "html.parser")
        for art in soup.find_all("article"):
            time_tag = art.find("time")
            if time_tag and CURRENT_YEAR in time_tag.get("datetime", ""):
                dt = time_tag.get("datetime", "")
                title_tag = art.find("h2"); 
                if not title_tag: continue
                baslik = title_tag.get_text(strip=True); link = title_tag.find("a")["href"]
                if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                
                list_img = get_universal_img(art, base_url)
                print(f"   🔎 İşleniyor: {baslik[:30]}...")
                
                inner_r = requests.get(link, timeout=15, headers=HEADERS)
                inner_img = get_universal_img(BeautifulSoup(inner_r.content, "html.parser").select_one('.single-post-thumb'), base_url)
                img = inner_img if inner_img else list_img
                
                tam_metin = extract_clean_text(inner_r.content, '.entry-content.articlebody')
                safe_create({"haber_basligi": baslik, "gorsel": img, "haber_metni": tam_metin, "yayin_tarihi": format_date(dt), "portal": portal_name, "url": link})
                ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                return # İLK HABERİ ATAR ATMAZ DURUR
    except Exception as e: print(f"Hata: {e}")

def scrape_makina_market(ex_urls, ex_titles):
    print(f"\n--- Tarama: Makina Market (Maks 1) ---")
    url = "https://makina-market.com.tr/category/haberler/"
    try:
        r = requests.get(url, timeout=20, headers=HEADERS)
        soup = BeautifulSoup(r.content, "html.parser")
        for art in soup.find_all("article"):
            title_tag = art.find("h2", class_="cs-entry__title")
            if not title_tag: continue
            link = title_tag.find("a")["href"]; baslik = title_tag.get_text(strip=True)
            if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
            
            dt_tag = art.find("div", class_="cs-meta-date")
            dt = dt_tag.get_text(strip=True) if dt_tag else ""
            
            list_img = get_universal_img(art, url)
            print(f"   🔎 İşleniyor: {baslik[:30]}...")
            
            inner_r = requests.get(link, timeout=20, headers=HEADERS)
            inner_img = get_universal_img(BeautifulSoup(inner_r.content, "html.parser").select_one('.cs-entry__thumbnail'), url)
            img = inner_img if inner_img else list_img
            
            tam_metin = extract_clean_text(inner_r.content, '.entry-content')
            safe_create({"haber_basligi": baslik, "gorsel": img, "haber_metni": tam_metin, "yayin_tarihi": format_date(dt), "portal": "Makina Market", "url": link})
            ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
            return # İLK HABERİ ATAR ATMAZ DURUR
    except Exception as e: print(f"Hata: {e}")

def scrape_formen(base_url, portal_name, ex_urls, ex_titles):
    print(f"\n--- Tarama: {portal_name} (Maks 1) ---")
    try:
        r = requests.get(base_url, timeout=20, headers=HEADERS)
        soup = BeautifulSoup(r.content, "html.parser")
        for item in soup.select(".tdb_module_loop, .td_module_wrap"):
            title_tag = item.find("h3", class_="entry-title")
            if not title_tag: continue
            link = title_tag.find("a")["href"]; baslik = title_tag.get_text(strip=True)
            if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
            
            list_img = get_universal_img(item, base_url)
            print(f"   🔎 İşleniyor: {baslik[:30]}...")
            
            inner_r = requests.get(link, timeout=20, headers=HEADERS)
            inner_soup = BeautifulSoup(inner_r.content, "html.parser")
            dt = inner_soup.find("time", class_="entry-date").get("datetime") if inner_soup.find("time", class_="entry-date") else ""
            
            inner_img = get_universal_img(inner_soup.select_one('.tdb_single_featured_image'), base_url)
            img = inner_img if inner_img else list_img
            
            tam_metin = extract_clean_text(inner_r.content, '.tdb_single_content')
            safe_create({"haber_basligi": baslik, "gorsel": img, "haber_metni": tam_metin, "yayin_tarihi": format_date(dt), "portal": portal_name, "url": link})
            ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
            return # İLK HABERİ ATAR ATMAZ DURUR
    except Exception as e: print(f"Hata: {e}")

def scrape_istif_mh(base_url, portal_name, ex_urls, ex_titles):
    print(f"\n--- Tarama: {portal_name} (Maks 1) ---")
    try:
        r = requests.get(base_url, timeout=20, headers=HEADERS)
        soup = BeautifulSoup(r.content, "html.parser")
        for item in soup.find_all("div", class_="kanews-post-item"):
            title_tag = item.find("h3", class_="kanews-post-headline")
            if not title_tag: continue
            link = title_tag.find("a")["href"]; baslik = title_tag.get_text(strip=True)
            if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
            
            list_img = get_universal_img(item, base_url)
            print(f"   🔎 İşleniyor: {baslik[:30]}...")
            
            inner_r = requests.get(link, timeout=20, headers=HEADERS)
            inner_soup = BeautifulSoup(inner_r.content, "html.parser")
            dt = inner_soup.find("time", class_="entry-date").get("datetime") if inner_soup.find("time", class_="entry-date") else ""
            
            inner_img = get_universal_img(inner_soup.select_one('.kanews-article-thumbnail'), base_url)
            img = inner_img if inner_img else list_img
            
            tam_metin = extract_clean_text(inner_r.content, '.entry-content-inner')
            safe_create({"haber_basligi": baslik, "gorsel": img, "haber_metni": tam_metin, "yayin_tarihi": format_date(dt), "portal": portal_name, "url": link})
            ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
            return # İLK HABERİ ATAR ATMAZ DURUR
    except Exception as e: print(f"Hata: {e}")

def scrape_santiye(ex_urls, ex_titles):
    print(f"\n--- Tarama: Şantiye (Maks 1) ---")
    url = "https://www.santiye.com.tr/haberler.html?page=1"
    try:
        r = requests.get(url, timeout=15, headers=HEADERS)
        soup = BeautifulSoup(r.content, "html.parser")
        for content in soup.find_all("div", class_="post-content"):
            date_tag = content.find("li")
            if date_tag and CURRENT_YEAR in date_tag.get_text():
                dt = date_tag.get_text(strip=True)
                a_tag = content.find("h2").find("a"); baslik = a_tag.get_text(strip=True)
                link = urljoin("https://www.santiye.com.tr", a_tag["href"])
                if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                
                parent_row = content.find_parent("div", class_="news-post")
                list_img = get_universal_img(parent_row, "https://www.santiye.com.tr")
                
                print(f"   🔎 İşleniyor: {baslik[:30]}...")
                inner_r = requests.get(link, timeout=15, headers=HEADERS)
                inner_img = get_universal_img(BeautifulSoup(inner_r.content, "html.parser").select_one('.post-gallery'), "https://www.santiye.com.tr")
                
                img = inner_img if inner_img else list_img
                
                tam_metin = extract_clean_text(inner_r.content, '.post-content', is_santiye=True)
                safe_create({"haber_basligi": baslik, "gorsel": img, "haber_metni": tam_metin, "yayin_tarihi": format_date(dt), "portal": "Şantiye", "url": link})
                ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                return # İLK HABERİ ATAR ATMAZ DURUR
    except Exception as e: print(f"Hata: {e}")

# ==========================================
# ANA ÇALIŞTIRICI
# ==========================================
if __name__ == "__main__":
    urls, titles = get_existing_data()
    print(f"📊 Başlıyoruz! Baserow'da Mevcut Kayıt Sayısı: {len(urls)}")
    
    scrape_forum_makina(urls, titles)
    scrape_newsplus_theme("https://www.lht.com.tr/kategori/haber/", "LHT", urls, titles)
    scrape_makina_market(urls, titles)
    
    scrape_formen("https://formendergisi.com/haber/", "Formen - Haber", urls, titles)
    scrape_formen("https://formendergisi.com/roportaj/", "Formen - Röportaj", urls, titles)
    scrape_formen("https://formendergisi.com/dunyadan/", "Formen - Dünya", urls, titles)
    
    scrape_istif_mh("https://istifmaterialhandling.com/category/haber/", "İstif MH - Haber", urls, titles)
    scrape_istif_mh("https://istifmaterialhandling.com/category/manset/", "İstif MH - Manşet", urls, titles)
    
    scrape_newsplus_theme("https://www.madenveocak.com.tr/kategori/haber/", "Maden Ocak Dergisi", urls, titles)
    scrape_santiye(urls, titles)
    
    print(f"\n🏁 İŞLEM TAMAMLANDI.")

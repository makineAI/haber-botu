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
# AYARLAR (YAPAY ZEKA KAPALI - KOTA GİTMEZ)
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
# NİHAİ ÇÖZÜM: OG:IMAGE (SOSYAL MEDYA KAPAĞI) AVCISI
# ==========================================
def get_article_cover_image(inner_soup, base_url):
    """WhatsApp ve Facebook'un kapak resmi çektiği meta etiketlerini kullanır. %100 kesin çözümdür."""
    if not inner_soup: return ""
    
    # 1. TAKTİK: Sitenin beynine gömülü orijinal kapak resmi (Tüm sitelerde standarttır)
    og_img = inner_soup.find("meta", property="og:image")
    if og_img and og_img.get("content"):
        url = og_img["content"].split('?')[0]
        if not url.startswith("http"): url = urljoin(base_url, url)
        return url.replace("http://", "https://")
        
    # 2. TAKTİK: Twitter kapak resmi (Yedek)
    tw_img = inner_soup.find("meta", attrs={"name": "twitter:image"})
    if tw_img and tw_img.get("content"):
        url = tw_img["content"].split('?')[0]
        if not url.startswith("http"): url = urljoin(base_url, url)
        return url.replace("http://", "https://")

    # 3. TAKTİK: Senin gönderdiğin HTML'ye göre Formen Özel
    formen_a = inner_soup.find("a", class_="td-modal-image")
    if formen_a and formen_a.get("href"):
        url = formen_a["href"].split('?')[0]
        if not url.startswith("http"): url = urljoin(base_url, url)
        return url.replace("http://", "https://")
        
    # 4. TAKTİK: Senin gönderdiğin HTML'ye göre Şantiye Özel
    santiye_img = inner_soup.select_one(".post-gallery img") or inner_soup.select_one("img.img-responsive")
    if santiye_img and santiye_img.get("src"):
        url = santiye_img["src"].split('?')[0]
        if not url.startswith("http"): url = urljoin(base_url, url)
        return url.replace("http://", "https://")

    return ""

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

    # YAPAY ZEKA KAPALI: Kota yememesi için analiz yapılmıyor
    fields["haber_ozeti"] = "Analiz Bekleniyor (Test)"
    fields["mai_analizi"] = "Analiz Bekleniyor (Test)"
    fields.pop("haber_metni", None)

    url = f"https://api.baserow.io/api/database/rows/table/{BASEROW_TABLE_ID}/?user_field_names=true"
    headers = {"Authorization": f"Token {BASEROW_TOKEN}", "Content-Type": "application/json"}
    try:
        res = requests.post(url, headers=headers, json=fields, timeout=20)
        if res.status_code == 200: print(f"   ✅ Kayıt Başarılı: {fields['haber_basligi'][:40]}...")
        else: print(f"   ❌ Kayıt Hatası: {res.text}")
    except Exception as e: print(f"   ❌ Bağlantı Hatası: {e}")

# ==========================================
# İÇ SAYFALARDAN GÖRSEL ALAN TARAYICILAR
# ==========================================
def scrape_forum_makina():
    print(f"\n--- Tarama: Forum Makina (Maks 1) ---")
    try:
        r = requests.get("https://www.forummakina.com.tr/tr/haberler?page=1", timeout=15, headers=HEADERS)
        soup = BeautifulSoup(r.content, "html.parser")
        for item in soup.find_all("li", class_="news"):
            date_text = item.find("div", class_="date").get_text(strip=True) if item.find("div", class_="date") else ""
            if CURRENT_YEAR in date_text:
                baslik = item.find("div", class_="title").get_text(strip=True)
                link = urljoin("https://www.forummakina.com.tr", item.find("a")["href"])
                
                print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
                inner_r = requests.get(link, timeout=15, headers=HEADERS)
                inner_soup = BeautifulSoup(inner_r.content, "html.parser")
                
                # Yeni Nesil Çekici
                img = get_article_cover_image(inner_soup, "https://www.forummakina.com.tr")
                
                safe_create({"haber_basligi": baslik, "gorsel": img, "haber_metni": "", "yayin_tarihi": format_date(date_text), "portal": "Forum Makina", "url": link})
                return 
    except Exception as e: print(f"Hata: {e}")

def scrape_formen(base_url, portal_name):
    print(f"\n--- Tarama: {portal_name} (Maks 1) ---")
    try:
        r = requests.get(base_url, timeout=20, headers=HEADERS)
        soup = BeautifulSoup(r.content, "html.parser")
        for item in soup.select(".tdb_module_loop, .td_module_wrap"):
            title_tag = item.find("h3", class_="entry-title")
            if not title_tag: continue
            link = title_tag.find("a")["href"]; baslik = title_tag.get_text(strip=True)
            
            print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
            inner_r = requests.get(link, timeout=20, headers=HEADERS)
            inner_soup = BeautifulSoup(inner_r.content, "html.parser")
            dt = inner_soup.find("time", class_="entry-date").get("datetime") if inner_soup.find("time", class_="entry-date") else ""
            
            # Yeni Nesil Çekici
            img = get_article_cover_image(inner_soup, base_url)
            
            safe_create({"haber_basligi": baslik, "gorsel": img, "haber_metni": "", "yayin_tarihi": format_date(dt), "portal": portal_name, "url": link})
            return 
    except Exception as e: print(f"Hata: {e}")

def scrape_santiye():
    print(f"\n--- Tarama: Şantiye (Maks 1) ---")
    try:
        r = requests.get("https://www.santiye.com.tr/haberler.html?page=1", timeout=15, headers=HEADERS)
        soup = BeautifulSoup(r.content, "html.parser")
        for content in soup.find_all("div", class_="post-content"):
            date_tag = content.find("li")
            if date_tag and CURRENT_YEAR in date_tag.get_text():
                dt = date_tag.get_text(strip=True)
                a_tag = content.find("h2").find("a"); baslik = a_tag.get_text(strip=True)
                link = urljoin("https://www.santiye.com.tr", a_tag["href"])
                
                print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
                inner_r = requests.get(link, timeout=15, headers=HEADERS)
                inner_soup = BeautifulSoup(inner_r.content, "html.parser")
                
                # Yeni Nesil Çekici
                img = get_article_cover_image(inner_soup, "https://www.santiye.com.tr")
                
                safe_create({"haber_basligi": baslik, "gorsel": img, "haber_metni": "", "yayin_tarihi": format_date(dt), "portal": "Şantiye", "url": link})
                return 
    except Exception as e: print(f"Hata: {e}")

def scrape_newsplus_theme(base_url, portal_name):
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
                
                print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
                inner_r = requests.get(link, timeout=15, headers=HEADERS)
                inner_soup = BeautifulSoup(inner_r.content, "html.parser")
                
                # Yeni Nesil Çekici
                img = get_article_cover_image(inner_soup, base_url)
                
                safe_create({"haber_basligi": baslik, "gorsel": img, "haber_metni": "", "yayin_tarihi": format_date(dt), "portal": portal_name, "url": link})
                return 
    except Exception as e: print(f"Hata: {e}")

def scrape_makina_market():
    print(f"\n--- Tarama: Makina Market (Maks 1) ---")
    try:
        r = requests.get("https://makina-market.com.tr/category/haberler/", timeout=20, headers=HEADERS)
        soup = BeautifulSoup(r.content, "html.parser")
        for art in soup.find_all("article"):
            title_tag = art.find("h2", class_="cs-entry__title")
            if not title_tag: continue
            link = title_tag.find("a")["href"]; baslik = title_tag.get_text(strip=True)
            dt_tag = art.find("div", class_="cs-meta-date")
            dt = dt_tag.get_text(strip=True) if dt_tag else ""
            
            print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
            inner_r = requests.get(link, timeout=20, headers=HEADERS)
            inner_soup = BeautifulSoup(inner_r.content, "html.parser")
            
            # Yeni Nesil Çekici
            img = get_article_cover_image(inner_soup, "https://makina-market.com.tr")
            
            safe_create({"haber_basligi": baslik, "gorsel": img, "haber_metni": "", "yayin_tarihi": format_date(dt), "portal": "Makina Market", "url": link})
            return 
    except Exception as e: print(f"Hata: {e}")

def scrape_istif_mh():
    print(f"\n--- Tarama: İstif MH - Haber (Maks 1) ---")
    try:
        r = requests.get("https://istifmaterialhandling.com/category/haber/", timeout=20, headers=HEADERS)
        soup = BeautifulSoup(r.content, "html.parser")
        for item in soup.find_all("div", class_="kanews-post-item"):
            title_tag = item.find("h3", class_="kanews-post-headline")
            if not title_tag: continue
            link = title_tag.find("a")["href"]; baslik = title_tag.get_text(strip=True)
            
            print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
            inner_r = requests.get(link, timeout=20, headers=HEADERS)
            inner_soup = BeautifulSoup(inner_r.content, "html.parser")
            dt = inner_soup.find("time", class_="entry-date").get("datetime") if inner_soup.find("time", class_="entry-date") else ""
            
            # Yeni Nesil Çekici
            img = get_article_cover_image(inner_soup, "https://istifmaterialhandling.com")
            
            safe_create({"haber_basligi": baslik, "gorsel": img, "haber_metni": "", "yayin_tarihi": format_date(dt), "portal": "İstif MH - Haber", "url": link})
            return 
    except Exception as e: print(f"Hata: {e}")


if __name__ == "__main__":
    print(f"📊 BAŞLIYORUZ! (Yapay Zeka Kapalı - Sadece 1'er Örnek)")
    
    scrape_forum_makina()
    scrape_santiye()
    
    scrape_formen("https://formendergisi.com/haber/", "Formen - Haber")
    scrape_formen("https://formendergisi.com/roportaj/", "Formen - Röportaj")
    scrape_formen("https://formendergisi.com/dunyadan/", "Formen - Dünya")
    
    scrape_makina_market()
    scrape_istif_mh()
    scrape_newsplus_theme("https://www.lht.com.tr/kategori/haber/", "LHT")
    scrape_newsplus_theme("https://www.madenveocak.com.tr/kategori/haber/", "Maden Ocak Dergisi")
    
    print(f"\n🏁 İŞLEM TAMAMLANDI.")

import os
import requests
import time
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from urllib.parse import urljoin, quote
from datetime import datetime
from google import genai

load_dotenv()
CURRENT_YEAR = str(datetime.now().year)

# ==========================================
# AYARLAR (BASEROW & GEMINI)
# ==========================================
BASEROW_TOKEN = os.environ.get('BASEROW_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
BASEROW_TABLE_ID = "1197624"

if not BASEROW_TOKEN or not GEMINI_API_KEY:
    print("❌ HATA: Şifreler bulunamadı!")
    exit()

client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# YARDIMCI FONKSİYONLAR
# ==========================================
def format_date(date_str):
    """Siteden gelen karmaşık tarihi Baserow'un anlayacağı YYYY-MM-DD formatına çevirir"""
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
    
    # Eğer zaten 2026-08-15 formatındaysa direkt al
    if len(date_str) >= 10 and date_str[4] == '-' and date_str[7] == '-':
        return date_str[:10]
        
    aylar = {
        "Ocak": "01", "Şubat": "02", "Mart": "03", "Nisan": "04", "Mayıs": "05", "Haziran": "06", 
        "Temmuz": "07", "Ağustos": "08", "Eylül": "09", "Ekim": "10", "Kasım": "11", "Aralık": "12",
        "Oca": "01", "Şub": "02", "Mar": "03", "Nis": "04", "May": "05", "Haz": "06", 
        "Tem": "07", "Ağu": "08", "Eyl": "09", "Eki": "10", "Kas": "11", "Ara": "12"
    }
    try:
        # Yılı bul
        match_year = re.search(r'202\d', date_str)
        year = match_year.group(0) if match_year else str(datetime.now().year)
        
        # Günü bul
        match_day = re.search(r'\b(0?[1-9]|[12][0-9]|3[01])\b', date_str)
        day = match_day.group(0).zfill(2) if match_day else "01"
        
        # Ayı bul
        month = "01"
        for tr, num in aylar.items():
            if tr.lower() in date_str.lower():
                month = num
                break
                
        # Eğer "15.08.2026" gibi noktalı/slajlı bir formattaysa:
        if month == "01":
            num_match = re.search(r'\b(0?[1-9]|[12][0-9]|3[01])[./-](0?[1-9]|1[012])[./-](202\d)\b', date_str)
            if num_match:
                return f"{num_match.group(3)}-{num_match.group(2).zfill(2)}-{num_match.group(1).zfill(2)}"
                
        return f"{year}-{month}-{day}"
    except:
        return datetime.now().strftime("%Y-%m-%d")

def yapay_zeka_ile_ozetle(haber_metni):
    try:
        prompt = f"Sen MAKİNE AI adında endüstriyel bir platformun editörüsün. Aşağıdaki haber metnini oku ve makine sektörü profesyonelleri için en önemli detayları içeren, maksimum 3 cümlelik vurucu bir özet çıkar:\n\n{haber_metni}"
        # YEPYENİ MODEL: gemini-3.6-flash (404 hatasını çözer)
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"   ⚠️ Özet çıkarma hatası: {e}")
        return "Özet oluşturulamadı."

def get_existing_data():
    ex_urls, ex_titles = set(), set()
    url = f"https://api.baserow.io/api/database/rows/table/{BASEROW_TABLE_ID}/?user_field_names=true&size=200"
    headers = {"Authorization": f"Token {BASEROW_TOKEN}"}
    
    print("🔄 Baserow'dan eski kayıtlar kontrol ediliyor... Lütfen bekleyin.")
    sayfa_sayisi = 1
    try:
        while url:
            res = requests.get(url, headers=headers, timeout=20).json()
            for r in res.get('results', []):
                u = r.get('url', '').strip().lower()
                t = r.get('haber_basligi', '').strip().lower()
                if u: ex_urls.add(u)
                if t: ex_titles.add(t)
            
            url = res.get('next')
            sayfa_sayisi += 1
            if sayfa_sayisi > 50: break
                
        return ex_urls, ex_titles
    except Exception as e:
        print(f"❌ Veri çekme hatası (Baserow): {e}")
        return set(), set()

def get_full_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.content, "html.parser")
        
        # Forum makina için regex genişletildi (news-detail eklendi)
        content = soup.find('article') or soup.find('div', class_=re.compile(r'content|post|entry|detay|news-detail|text', re.I))
        if content:
            paragraphs = content.find_all('p')
        else:
            paragraphs = soup.find_all('p')
            
        text = " ".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        return text
    except Exception as e:
        print(f"   ⚠️ Tam metin çekilemedi: {url} | Hata: {e}")
        return ""

def upload_image_to_baserow(img_url):
    if not img_url or "data:image" in img_url: return None
    
    # print(f"   📸 Görsel Baserow'a yükleniyor...") # Logları temizlemek için kapattık
    url = "https://api.baserow.io/api/user-files/upload-via-url/"
    headers = {
        "Authorization": f"Token {BASEROW_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        res = requests.post(url, headers=headers, json={"url": img_url}, timeout=20)
        if res.status_code == 200:
            return res.json().get("name")
        else:
            print(f"   ⚠️ Görsel web sitesi tarafından gizlenmiş, metin kaydedilecek.")
            return None
    except:
        return None

def safe_create(fields):
    # 1. GÖRSEL İŞLEMİ
    gorsel_verisi = fields.get("gorsel", "")
    img_url = ""
    if isinstance(gorsel_verisi, list) and len(gorsel_verisi) > 0:
        img_url = gorsel_verisi[0].get("url", "")
        
    uploaded_name = upload_image_to_baserow(img_url) if img_url else None
    
    if uploaded_name:
        fields["gorsel"] = [{"name": uploaded_name}]
    else:
        fields["gorsel"] = []

    # 2. ÖZET İŞLEMİ
    metin = fields.get("haber_metni", "")
    if metin and len(metin) > 100:
        print(f"   🤖 Gemini özetliyor...")
        fields["haber_ozeti"] = yapay_zeka_ile_ozetle(metin)
    else:
        fields["haber_ozeti"] = "Metin çok kısa, özet oluşturulamadı."

    # 3. KAYIT İŞLEMİ (yayin_tarihi eklendi)
    url = f"https://api.baserow.io/api/database/rows/table/{BASEROW_TABLE_ID}/?user_field_names=true"
    headers = {
        "Authorization": f"Token {BASEROW_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, headers=headers, json=fields, timeout=20)
        if response.status_code == 200:
            print(f"   ✅ Baserow'a Kaydedildi: {fields['haber_basligi'][:40]}...")
        else:
            print(f"   ❌ HATA ({response.status_code}): {response.text}")
        time.sleep(1)
    except Exception as e:
        print(f"   ❌ HATA (Bağlantı koptu): {e}")

def clean_img(url, base_url):
    if not url or "data:image" in url: return ""
    try:
        actual_url = url.replace('&quot;', '').replace('"', '').replace("'", "").strip()
        return urljoin(base_url, actual_url).replace("http://", "https://")
    except: return ""

def extract_formen_img(item):
    span_tag = item.find("span", {"data-img-url": True})
    if span_tag: return span_tag.get("data-img-url")
    span_style = item.find("span", class_="entry-thumb")
    if span_style and span_style.get("style"):
        style_str = span_style.get("style")
        match = re.search(r'url\((.*?)\)', style_str)
        if match: return match.group(1)
    img_tag = item.find("img")
    if img_tag: return img_tag.get("data-src") or img_tag.get("src")
    return ""

# ==========================================
# 1. FORUM MAKİNA
# ==========================================
def scrape_forum_makina(ex_urls, ex_titles):
    print(f"\n--- [1/10] Forum Makina (Maks 1) ---")
    headers = {'User-Agent': 'Mozilla/5.0'}
    count = 0
    for page in range(1, 2):
        url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        try:
            r = requests.get(url, timeout=15, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            items = soup.find_all("li", class_="news")
            for item in items:
                if count >= 1: return
                date_text = item.find("div", class_="date").get_text(strip=True) if item.find("div", class_="date") else ""
                if CURRENT_YEAR in date_text:
                    baslik = item.find("div", class_="title").get_text(strip=True)
                    link = urljoin("https://www.forummakina.com.tr", item.find("a")["href"])
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img = clean_img(item.find("img")["src"], url) if item.find("img") else ""
                    
                    print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
                    tam_metin = get_full_text(link)
                    
                    # Gerçek yayın tarihi fonksiyona gönderiliyor
                    gercek_tarih = format_date(date_text)
                    
                    safe_create({"haber_basligi": baslik, "gorsel": [{"url": img}] if img else [], "haber_metni": tam_metin, "yayin_tarihi": gercek_tarih, "portal": "Forum Makina", "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                    count += 1
        except: continue

# ==========================================
# 2. LHT
# ==========================================
def scrape_lht(ex_urls, ex_titles):
    print(f"\n--- [2/10] LHT (Maks 1) ---")
    count = 0
    for page in range(1, 2):
        url = f"https://www.lht.com.tr/kategori/haber/page/{page}/" if page > 1 else "https://www.lht.com.tr/kategori/haber/"
        try:
            r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(r.content, "html.parser")
            for art in soup.find_all("article"):
                if count >= 1: return
                dt = art.find("time").get("datetime", "") if art.find("time") else ""
                if CURRENT_YEAR in dt:
                    title_tag = art.find("h2")
                    baslik = title_tag.get_text(strip=True); link = title_tag.find("a")["href"]
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img = art.find("img")["src"] if art.find("img") else ""
                    
                    print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
                    tam_metin = get_full_text(link)
                    gercek_tarih = format_date(dt)
                    
                    safe_create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img, url)}] if img else [], "haber_metni": tam_metin, "yayin_tarihi": gercek_tarih, "portal": "LHT", "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                    count += 1
        except: continue

# ==========================================
# 3. MAKİNA MARKET
# ==========================================
def scrape_makina_market(ex_urls, ex_titles):
    print(f"\n--- [3/10] Makina Market (Maks 1) ---")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    count = 0
    for page in range(1, 2):
        url = f"https://makina-market.com.tr/category/haberler/page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            articles = soup.find_all("article")
            for art in articles:
                if count >= 1: return
                title_tag = art.find("h2")
                if not title_tag: continue
                link = title_tag.find("a")["href"]
                baslik = title_tag.get_text(strip=True)
                if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                
                time_tag = art.find("time")
                dt = time_tag.get("datetime") or time_tag.get_text() if time_tag else ""
                
                img_tag = art.find("img")
                img_src = img_tag.get("data-src") or img_tag.get("src") if img_tag else ""
                
                print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
                tam_metin = get_full_text(link)
                gercek_tarih = format_date(dt)
                
                safe_create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, url)}] if img_src else [], "haber_metni": tam_metin, "yayin_tarihi": gercek_tarih, "portal": "Makina Market", "url": link})
                ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                count += 1
        except: continue

# ==========================================
# 4, 5, 6. FORMEN
# ==========================================
def process_formen(base_url, portal_name, ex_urls, ex_titles):
    print(f"\n--- Tarama: {portal_name} (Maks 1) ---")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
    count = 0
    for page in range(1, 2):
        url = f"{base_url}page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            items = soup.select(".tdb_module_loop, .td_module_wrap, .td_module_10, .td_module_mx1")
            for item in items:
                if count >= 1: return
                title_tag = item.find("h3") or item.find("h2")
                if not title_tag or not title_tag.find("a"): continue
                link = title_tag.find("a")["href"]
                baslik = title_tag.get_text(strip=True)
                if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                
                time_tag = item.find("time")
                dt = time_tag.get("datetime") or time_tag.get_text() if time_tag else ""
                
                img_src = extract_formen_img(item)
                
                print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
                tam_metin = get_full_text(link)
                gercek_tarih = format_date(dt)
                
                safe_create({
                    "haber_basligi": baslik, 
                    "gorsel": [{"url": clean_img(img_src, url)}] if img_src else [], 
                    "haber_metni": tam_metin,
                    "yayin_tarihi": gercek_tarih,
                    "portal": portal_name, 
                    "url": link
                })
                ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                count += 1
        except: continue

# ==========================================
# 7, 8. İSTİF MH
# ==========================================
def process_istif_mh(base_url, portal_name, ex_urls, ex_titles):
    print(f"\n--- Tarama: {portal_name} (Maks 1) ---")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    count = 0
    for page in range(1, 2):
        url = f"{base_url}page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            items = soup.find_all("div", class_="kanews-post-item")
            for item in items:
                if count >= 1: return
                title_tag = item.find("h3")
                if not title_tag: continue
                link = title_tag.find("a")["href"]
                baslik = title_tag.get_text(strip=True)
                if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                
                time_tag = item.find("span", class_="kanews-date")
                dt = time_tag.get_text(strip=True) if time_tag else ""
                
                img_tag = item.find("img")
                img_src = img_tag.get("src") or img_tag.get("data-src") if img_tag else ""
                
                is_valid = False
                if (img_src and f"/{CURRENT_YEAR}/" in img_src) or (CURRENT_YEAR in item.get_text()):
                    is_valid = True
                
                if not is_valid:
                    try:
                        inner_r = requests.get(link, timeout=10, headers=headers)
                        if f"/{CURRENT_YEAR}/" in inner_r.text: is_valid = True
                    except: pass

                if is_valid:
                    print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
                    tam_metin = get_full_text(link)
                    gercek_tarih = format_date(dt)
                    
                    safe_create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, url)}] if img_src else [], "haber_metni": tam_metin, "yayin_tarihi": gercek_tarih, "portal": portal_name, "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                    count += 1
                else:
                    pass
        except: continue

# ==========================================
# 9. MADEN OCAK
# ==========================================
def scrape_maden_ocak(ex_urls, ex_titles):
    print(f"\n--- [9/10] Maden Ocak (Maks 1) ---")
    headers = {'User-Agent': 'Mozilla/5.0'}
    count = 0
    for page in range(1, 2):
        url = f"https://www.madenveocak.com.tr/kategori/haber/page/{page}/"
        try:
            r = requests.get(url, timeout=15, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            for art in soup.find_all("article"):
                if count >= 1: return
                time_tag = art.find("time")
                if time_tag and CURRENT_YEAR in time_tag.get("datetime", ""):
                    dt = time_tag.get("datetime", "")
                    title_tag = art.find("h2"); link = title_tag.find("a")["href"]; baslik = title_tag.get_text(strip=True)
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img_tag = art.find("img"); img_src = img_tag.get("src", "") if img_tag else ""
                    
                    print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
                    tam_metin = get_full_text(link)
                    gercek_tarih = format_date(dt)
                    
                    safe_create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, url)}] if img_src else [], "haber_metni": tam_metin, "yayin_tarihi": gercek_tarih, "portal": "Maden Ocak Dergisi", "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                    count += 1
        except: continue

# ==========================================
# 10. ŞANTİYE
# ==========================================
def scrape_santiye(ex_urls, ex_titles):
    print(f"\n--- [10/10] Şantiye (Maks 1) ---")
    headers = {'User-Agent': 'Mozilla/5.0'}
    count = 0
    for page in range(1, 2):
        url = f"https://www.santiye.com.tr/haberler.html?page={page}"
        try:
            r = requests.get(url, timeout=15, headers=headers)
            soup = BeautifulSoup(r.content, "html.parser")
            for content in soup.find_all("div", class_="post-content"):
                if count >= 1: return
                date_tag = content.find("li")
                if date_tag and CURRENT_YEAR in date_tag.get_text():
                    dt = date_tag.get_text(strip=True)
                    title_tag = content.find("h2"); a_tag = title_tag.find("a"); baslik = a_tag.get_text(strip=True)
                    link = urljoin("https://www.santiye.com.tr", a_tag["href"])
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    row = content.find_parent("div", class_="row"); img_src = row.find("img").get("src", "") if row and row.find("img") else ""
                    
                    print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
                    tam_metin = get_full_text(link)
                    gercek_tarih = format_date(dt)
                    
                    safe_create({"haber_basligi": baslik, "gorsel": [{"url": clean_img(img_src, "https://www.santiye.com.tr")}] if img_src else [], "haber_metni": tam_metin, "yayin_tarihi": gercek_tarih, "portal": "Şantiye", "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                    count += 1
        except: continue

# ==========================================
# ANA ÇALIŞTIRICI
# ==========================================
if __name__ == "__main__":
    urls, titles = get_existing_data()
    print(f"📊 Başlıyoruz! Baserow'da Mevcut Kayıt Sayısı: {len(urls)}")
    
    scrape_forum_makina(urls, titles)
    scrape_lht(urls, titles)
    scrape_makina_market(urls, titles)
    
    process_formen("https://formendergisi.com/haber/", "Formen - Haber", urls, titles)
    process_formen("https://formendergisi.com/roportaj/", "Formen - Röportaj", urls, titles)
    process_formen("https://formendergisi.com/dunyadan/", "Formen - Dünya", urls, titles)
    
    process_istif_mh("https://istifmaterialhandling.com/category/haber/", "İstif MH - Haber", urls, titles)
    process_istif_mh("https://istifmaterialhandling.com/category/manset/", "İstif MH - Manşet", urls, titles)
    scrape_maden_ocak(urls, titles)
    scrape_santiye(urls, titles)
    
    print(f"\n🏁 İŞLEM TAMAMLANDI.")

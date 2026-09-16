import os
import requests
import time
import re
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from urllib.parse import urljoin
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

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive'
}

# ==========================================
# YARDIMCI FONKSİYONLAR
# ==========================================
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
            if tr.lower() in date_str.lower():
                month = num
                break
        if month == "01":
            num_match = re.search(r'\b(0?[1-9]|[12][0-9]|3[01])[./-](0?[1-9]|1[012])[./-](202\d)\b', date_str)
            if num_match: return f"{num_match.group(3)}-{num_match.group(2).zfill(2)}-{num_match.group(1).zfill(2)}"
        return f"{year}-{month}-{day}"
    except: return datetime.now().strftime("%Y-%m-%d")

def yapay_zeka_ile_ozetle_ve_analiz_et(haber_metni, deneme_sayisi=0):
    # XML Kalkanı: Yapay Zeka formatı asla bozamaz
    prompt = f"""Sen MAKİNE AI platformunun baş editörü ve baş analistisin. 
Aşağıdaki haberi oku ve bana YALNIZCA aşağıdaki XML etiketleri (tag) arasında çıktı ver. Başka hiçbir açıklama yazma.

<ozet>
Haberin kritik noktalarını 3-4 maddelik (tire ile), KISA ve ÖZ bir şekilde özetle. Önemli rakamları veya kilit kelimeleri Markdown formatında (**kalın**) vurgula.
</ozet>
<analiz>
Bu haberin sektöre (iş makineleri, istifleme, inşaat vb.) etkisini 1 veya 2 cümle ile çok kısa belirt.
</analiz>

Haber Metni:
{haber_metni}"""

    try:
        time.sleep(4) # Kotayı korumak için kısa uyku
        response = client.models.generate_content(model='gemini-1.5-flash', contents=prompt)
        text = response.text
        
        # Etiketlerin içini %100 başarıyla çeken regex (arama) motoru
        ozet_match = re.search(r'<ozet>(.*?)</ozet>', text, re.DOTALL | re.IGNORECASE)
        analiz_match = re.search(r'<analiz>(.*?)</analiz>', text, re.DOTALL | re.IGNORECASE)
        
        if ozet_match and analiz_match:
            return ozet_match.group(1).strip(), analiz_match.group(1).strip()
        else:
            return text.strip(), "MAI Analizi XML formatına uymadı."
            
    except Exception as e:
        hata_mesaji = str(e)
        if "429" in hata_mesaji or "RESOURCE_EXHAUSTED" in hata_mesaji:
            if deneme_sayisi < 3:
                print(f"   ⏳ Google Limiti! 30 saniye bekleniyor... (Deneme: {deneme_sayisi+1}/3)")
                time.sleep(30)
                return yapay_zeka_ile_ozetle_ve_analiz_et(haber_metni, deneme_sayisi + 1)
            else: return "Özet çıkarılamadı (Limit Aşıldı).", "Analiz Yapılamadı."
        else: return "Yapay Zeka Hatası.", f"Detay: {e}"

def get_existing_data():
    ex_urls, ex_titles = set(), set()
    url = f"https://api.baserow.io/api/database/rows/table/{BASEROW_TABLE_ID}/?user_field_names=true&size=200"
    headers = {"Authorization": f"Token {BASEROW_TOKEN}"}
    print("🔄 Baserow'dan eski kayıtlar kontrol ediliyor...")
    try:
        sayfa_sayisi = 1
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
    except Exception: return set(), set()

def clean_html(soup):
    garbage = ['.share', '.twit', 'script', 'style', '.pk-share-buttons-wrap', '#comments', '.cs-entry__subscribe', '#related-articles', '.td-post-sharing', '.tdb_single_tags', '.tdb_single_comments', '#newsletter', '.kanews-reading-bar', '.kanews-article-action', '.sharethis-inline-share-buttons', '.post-tags', '.post-views']
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
    if not paragraphs:
        backup_text = content.get_text(separator="\n", strip=True)
        if len(backup_text) > 50: return backup_text
    return "\n".join(paragraphs)

# YENİ NESİL KUSURSUZ GÖRSEL AVCISI
def get_image_url(soup_context, base_url):
    if not soup_context: return ""
    url = ""
    
    if hasattr(soup_context, 'find'):
        # 1. Formen için data-img-url (Gizli Resimler)
        tag_data = soup_context.find(attrs={"data-img-url": True})
        if tag_data: url = tag_data['data-img-url']
        
        # 2. Tembel yükleme (Lazy load)
        if not url:
            tag_lazy = soup_context.find(attrs={"data-src": True})
            if tag_lazy: url = tag_lazy['data-src']
            
        # 3. Klasik src
        if not url:
            tag_img = soup_context.find("img")
            if tag_img and tag_img.has_attr("src"): url = tag_img["src"]
            
    # Eğer gönderilen elementin ta kendisi bir resim etiketi ise
    if not url and hasattr(soup_context, 'has_attr'):
        if soup_context.has_attr('data-img-url'): url = soup_context['data-img-url']
        elif soup_context.has_attr('data-src'): url = soup_context['data-src']
        elif soup_context.name == 'img' and soup_context.has_attr('src'): url = soup_context['src']

    if not url or "data:image" in url or "base64" in url: return ""
    
    # ?v=1.0 gibi versiyon eklentilerini tamamen parçala ve at
    actual_url = url.replace('&quot;', '').replace('"', '').replace("'", "").strip().split('?')[0]
    return urljoin(base_url, actual_url).replace("http://", "https://")

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

    metin = fields.get("haber_metni", "")
    if metin and len(metin) > 50: 
        print(f"   🤖 Gemini analiz ediyor... ({len(metin)} Karakter)")
        ozet, analiz = yapay_zeka_ile_ozetle_ve_analiz_et(metin)
        fields["haber_ozeti"] = ozet
        fields["mai_analizi"] = analiz
    else:
        print(f"   ⚠️ HATA: Metin okunamadı!")
        fields["haber_ozeti"] = "Metin tespit edilemedi."
        fields["mai_analizi"] = "-"

    fields.pop("haber_metni", None)

    url = f"https://api.baserow.io/api/database/rows/table/{BASEROW_TABLE_ID}/?user_field_names=true"
    headers = {"Authorization": f"Token {BASEROW_TOKEN}", "Content-Type": "application/json"}
    try:
        response = requests.post(url, headers=headers, json=fields, timeout=20)
        if response.status_code == 200: print(f"   ✅ Kayıt Başarılı: {fields['haber_basligi'][:40]}...")
        else: print(f"   ❌ Kayıt Hatası: {response.text}")
    except Exception as e: print(f"   ❌ Bağlantı Koptu: {e}")


# ==========================================
# 1. FORUM MAKİNA
# ==========================================
def scrape_forum_makina(ex_urls, ex_titles):
    print(f"\n--- [1/10] Forum Makina (Maks 1) ---")
    for page in range(1, 2):
        url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        try:
            r = requests.get(url, timeout=15, headers=HEADERS)
            soup = BeautifulSoup(r.content, "html.parser")
            for item in soup.find_all("li", class_="news"):
                date_text = item.find("div", class_="date").get_text(strip=True) if item.find("div", class_="date") else ""
                if CURRENT_YEAR in date_text:
                    baslik = item.find("div", class_="title").get_text(strip=True)
                    link = urljoin("https://www.forummakina.com.tr", item.find("a")["href"])
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    
                    list_img = get_image_url(item, url)
                    print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
                    inner_r = requests.get(link, timeout=15, headers=HEADERS)
                    inner_soup = BeautifulSoup(inner_r.content, "html.parser")
                    
                    inner_img = get_image_url(inner_soup.select_one('.newsDetail'), "https://www.forummakina.com.tr")
                    img = inner_img if inner_img else list_img
                    
                    tam_metin = extract_clean_text(inner_r.content, '.newsDetail')
                    safe_create({"haber_basligi": baslik, "gorsel": img, "haber_metni": tam_metin, "yayin_tarihi": format_date(date_text), "portal": "Forum Makina", "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                    return 
        except Exception as e: print(f"Hata: {e}")

# ==========================================
# 2. LHT & 6. MADEN OCAK
# ==========================================
def scrape_newsplus_theme(base_url, portal_name, ex_urls, ex_titles):
    print(f"\n--- Tarama: {portal_name} (Maks 1) ---")
    for page in range(1, 2):
        url = f"{base_url}page/{page}/" if page > 1 else base_url
        try:
            r = requests.get(url, timeout=15, headers=HEADERS)
            soup = BeautifulSoup(r.content, "html.parser")
            for art in soup.find_all("article"):
                time_tag = art.find("time")
                if time_tag and CURRENT_YEAR in time_tag.get("datetime", ""):
                    dt = time_tag.get("datetime", "")
                    title_tag = art.find("h2")
                    if not title_tag: continue
                    baslik = title_tag.get_text(strip=True); link = title_tag.find("a")["href"]
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    
                    list_img = get_image_url(art, url)
                    print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
                    inner_r = requests.get(link, timeout=15, headers=HEADERS)
                    inner_soup = BeautifulSoup(inner_r.content, "html.parser")
                    
                    inner_img = get_image_url(inner_soup.select_one('.single-post-thumb'), base_url)
                    img = inner_img if inner_img else list_img
                    
                    tam_metin = extract_clean_text(inner_r.content, '.entry-content.articlebody')
                    safe_create({"haber_basligi": baslik, "gorsel": img, "haber_metni": tam_metin, "yayin_tarihi": format_date(dt), "portal": portal_name, "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                    return 
        except Exception as e: print(f"Hata: {e}")

# ==========================================
# 3. MAKİNA MARKET
# ==========================================
def scrape_makina_market(ex_urls, ex_titles):
    print(f"\n--- [3/10] Makina Market (Maks 1) ---")
    for page in range(1, 2):
        url = f"https://makina-market.com.tr/category/haberler/page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers=HEADERS)
            soup = BeautifulSoup(r.content, "html.parser")
            for art in soup.find_all("article"):
                title_tag = art.find("h2", class_="cs-entry__title")
                if not title_tag: continue
                link = title_tag.find("a")["href"]; baslik = title_tag.get_text(strip=True)
                if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                
                dt = art.find("div", class_="cs-meta-date").get_text(strip=True) if art.find("div", class_="cs-meta-date") else ""
                list_img = get_image_url(art, url)
                
                print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
                inner_r = requests.get(link, timeout=20, headers=HEADERS)
                inner_soup = BeautifulSoup(inner_r.content, "html.parser")
                
                inner_img = get_image_url(inner_soup.select_one('.cs-entry__thumbnail'), url)
                img = inner_img if inner_img else list_img
                
                tam_metin = extract_clean_text(inner_r.content, '.entry-content')
                safe_create({"haber_basligi": baslik, "gorsel": img, "haber_metni": tam_metin, "yayin_tarihi": format_date(dt), "portal": "Makina Market", "url": link})
                ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                return
        except Exception as e: print(f"Hata: {e}")

# ==========================================
# 4. FORMEN GRUBU
# ==========================================
def scrape_formen(base_url, portal_name, ex_urls, ex_titles):
    print(f"\n--- Tarama: {portal_name} (Maks 1) ---")
    for page in range(1, 2):
        url = f"{base_url}page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers=HEADERS)
            soup = BeautifulSoup(r.content, "html.parser")
            for item in soup.select(".tdb_module_loop, .td_module_wrap"):
                title_tag = item.find("h3", class_="entry-title")
                if not title_tag: continue
                link = title_tag.find("a")["href"]; baslik = title_tag.get_text(strip=True)
                if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                
                list_img = get_image_url(item, url)
                print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
                inner_r = requests.get(link, timeout=20, headers=HEADERS)
                inner_soup = BeautifulSoup(inner_r.content, "html.parser")
                
                dt = inner_soup.find("time", class_="entry-date").get("datetime") if inner_soup.find("time", class_="entry-date") else ""
                inner_img = get_image_url(inner_soup.select_one('.tdb_single_featured_image'), url)
                img = inner_img if inner_img else list_img
                
                tam_metin = extract_clean_text(inner_r.content, '.tdb_single_content')
                safe_create({"haber_basligi": baslik, "gorsel": img, "haber_metni": tam_metin, "yayin_tarihi": format_date(dt), "portal": portal_name, "url": link})
                ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                return
        except Exception as e: print(f"Hata: {e}")

# ==========================================
# 5. İSTİF MH GRUBU
# ==========================================
def scrape_istif_mh(base_url, portal_name, ex_urls, ex_titles):
    print(f"\n--- Tarama: {portal_name} (Maks 1) ---")
    for page in range(1, 2):
        url = f"{base_url}page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers=HEADERS)
            soup = BeautifulSoup(r.content, "html.parser")
            for item in soup.find_all("div", class_="kanews-post-item"):
                title_tag = item.find("h3", class_="kanews-post-headline")
                if not title_tag: continue
                link = title_tag.find("a")["href"]; baslik = title_tag.get_text(strip=True)
                if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                
                list_img = get_image_url(item, url)
                print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
                inner_r = requests.get(link, timeout=20, headers=HEADERS)
                inner_soup = BeautifulSoup(inner_r.content, "html.parser")
                
                dt = inner_soup.find("time", class_="entry-date").get("datetime") if inner_soup.find("time", class_="entry-date") else ""
                inner_img = get_image_url(inner_soup.select_one('.kanews-article-thumbnail'), url)
                img = inner_img if inner_img else list_img
                
                tam_metin = extract_clean_text(inner_r.content, '.entry-content-inner')
                safe_create({"haber_basligi": baslik, "gorsel": img, "haber_metni": tam_metin, "yayin_tarihi": format_date(dt), "portal": portal_name, "url": link})
                ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                return
        except Exception as e: print(f"Hata: {e}")

# ==========================================
# 7. ŞANTİYE
# ==========================================
def scrape_santiye(ex_urls, ex_titles):
    print(f"\n--- [10/10] Şantiye (Maks 1) ---")
    for page in range(1, 2):
        url = f"https://www.santiye.com.tr/haberler.html?page={page}"
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
                    
                    list_img = get_image_url(content.find_parent("div", class_="news-post"), "https://www.santiye.com.tr")
                    
                    print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
                    inner_r = requests.get(link, timeout=15, headers=HEADERS)
                    inner_soup = BeautifulSoup(inner_r.content, "html.parser")
                    
                    inner_img = get_image_url(inner_soup.select_one('.post-gallery'), "https://www.santiye.com.tr")
                    img = inner_img if inner_img else list_img
                    
                    tam_metin = extract_clean_text(inner_r.content, '.post-content', is_santiye=True)
                    safe_create({"haber_basligi": baslik, "gorsel": img, "haber_metni": tam_metin, "yayin_tarihi": format_date(dt), "portal": "Şantiye", "url": link})
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
                    return
        except Exception as e: print(f"Hata: {e}")

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

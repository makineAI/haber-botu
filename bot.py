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
# AYARLAR
# ==========================================
BASEROW_TOKEN = os.environ.get('BASEROW_TOKEN')
BASEROW_TABLE_ID = "1197624"

if not BASEROW_TOKEN:
    print("❌ HATA: Baserow şifresi bulunamadı!")
    exit()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
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
# GÜVENLİ GÖRSEL YÜKLEYİCİ (UPLOAD-FILE)
# ==========================================
def upload_image_to_baserow(img_url):
    """
    Baserow sunucusunun hotlink engeline takılmaması için görseli
    önce bot kendi User-Agent'ı ile indirir, sonra doğrudan Baserow'a yükler.
    """
    if not img_url:
        return None
    try:
        img_res = requests.get(img_url, headers=HEADERS, timeout=15)
        if img_res.status_code != 200 or len(img_res.content) < 200:
            print(f"   ⚠️ Görsel kaynaktan indirilemedi (HTTP {img_res.status_code})")
            return None

        clean_name = img_url.split('/')[-1].split('?')[0]
        if not clean_name.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            clean_name += ".jpg"

        upload_url = "https://api.baserow.io/api/user-files/upload-file/"
        headers = {"Authorization": f"Token {BASEROW_TOKEN}"}
        files = {"file": (clean_name, img_res.content)}

        res = requests.post(upload_url, headers=headers, files=files, timeout=25)
        if res.status_code in [200, 201]:
            uploaded_name = res.json().get("name")
            print(f"   📥 Baserow Dosyası Oluştu: {uploaded_name}")
            return uploaded_name
        else:
            print(f"   ❌ Baserow Yükleme Hatası ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"   ❌ Görsel Aktarım Hatası: {e}")
    return None

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

def safe_create(fields):
    img_url = fields.get("gorsel", "")
    print(f"   📸 Bulunan Görsel URL: {img_url if img_url else 'YOK'}")

    uploaded_name = upload_image_to_baserow(img_url) if img_url else None
    fields["gorsel"] = [{"name": uploaded_name}] if uploaded_name else []

    fields["haber_ozeti"] = "Analiz Bekleniyor"
    fields["mai_analizi"] = "-"
    fields.pop("haber_metni", None)

    url = f"https://api.baserow.io/api/database/rows/table/{BASEROW_TABLE_ID}/?user_field_names=true"
    headers = {"Authorization": f"Token {BASEROW_TOKEN}", "Content-Type": "application/json"}
    try:
        res = requests.post(url, headers=headers, json=fields, timeout=20)
        if res.status_code in [200, 201]:
            print(f"   ✅ Kayıt Başarılı: {fields['haber_basligi'][:40]}...")
        else:
            print(f"   ❌ Kayıt Hatası: {res.text}")
    except Exception as e:
        print(f"   ❌ Bağlantı Hatası: {e}")

# ==========================================
# SİTE TARAYICILARI
# ==========================================

def scrape_forum_makina():
    print(f"\n--- Tarama: Forum Makina ---")
    try:
        r = requests.get("https://www.forummakina.com.tr/tr/haberler?page=1", timeout=15, headers=HEADERS)
        soup = BeautifulSoup(r.content, "html.parser")
        for item in soup.find_all("li", class_="news"):
            baslik_div = item.find("div", class_="title")
            if not baslik_div: continue
            baslik = baslik_div.get_text(strip=True)
            link = urljoin("https://www.forummakina.com.tr", item.find("a")["href"])
            date_text = item.find("div", class_="date").get_text(strip=True) if item.find("div", class_="date") else ""

            # 1. Vitrindeki küçük görsel
            vitrin_img = ""
            list_img_tag = item.find("img")
            if list_img_tag and list_img_tag.get("src"):
                vitrin_img = urljoin("https://www.forummakina.com.tr", list_img_tag["src"])

            print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
            inner_r = requests.get(link, timeout=15, headers=HEADERS)
            inner_soup = BeautifulSoup(inner_r.content, "html.parser")

            # 2. İç sayfadaki ana görsel
            detay_img = inner_soup.find("img", src=re.compile(r"gallery/news", re.I))
            img_url = urljoin("https://www.forummakina.com.tr", detay_img["src"]) if (detay_img and detay_img.get("src")) else vitrin_img

            tam_metin = extract_clean_text(inner_r.content, '.newsDetail')
            safe_create({"haber_basligi": baslik, "gorsel": img_url, "haber_metni": tam_metin, "yayin_tarihi": format_date(date_text), "portal": "Forum Makina", "url": link})
            return
    except Exception as e: print(f"Hata: {e}")

def scrape_formen(base_url, portal_name):
    print(f"\n--- Tarama: {portal_name} ---")
    try:
        r = requests.get(base_url, timeout=20, headers=HEADERS)
        soup = BeautifulSoup(r.content, "html.parser")
        for item in soup.select(".tdb_module_loop, .td_module_wrap"):
            title_tag = item.find("h3", class_="entry-title")
            if not title_tag: continue
            link = title_tag.find("a")["href"]
            baslik = title_tag.get_text(strip=True)

            # 1. Vitrindeki data-img-url
            vitrin_img = ""
            span_tag = item.find("span", attrs={"data-img-url": True})
            if span_tag: vitrin_img = span_tag["data-img-url"]

            print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
            inner_r = requests.get(link, timeout=20, headers=HEADERS)
            inner_soup = BeautifulSoup(inner_r.content, "html.parser")
            time_tag = inner_soup.find("time", class_="entry-date")
            dt = time_tag.get("datetime") if time_tag else ""

            # 2. İç sayfadaki td-modal-image veya entry-thumb
            img_url = ""
            a_modal = inner_soup.find("a", class_="td-modal-image")
            img_thumb = inner_soup.find("img", class_=re.compile(r"entry-thumb", re.I))

            if a_modal and a_modal.get("href"):
                img_url = a_modal["href"]
            elif img_thumb and img_thumb.get("src"):
                img_url = img_thumb["src"]
            else:
                img_url = vitrin_img

            if img_url:
                img_url = img_url.split("?")[0].strip()
                if not img_url.startswith("http"): img_url = urljoin(base_url, img_url)

            tam_metin = extract_clean_text(inner_r.content, '.tdb_single_content')
            safe_create({"haber_basligi": baslik, "gorsel": img_url, "haber_metni": tam_metin, "yayin_tarihi": format_date(dt), "portal": portal_name, "url": link})
            return
    except Exception as e: print(f"Hata: {e}")

def scrape_santiye():
    print(f"\n--- Tarama: Şantiye ---")
    try:
        r = requests.get("https://www.santiye.com.tr/haberler.html?page=1", timeout=15, headers=HEADERS)
        soup = BeautifulSoup(r.content, "html.parser")
        for content in soup.find_all("div", class_="post-content"):
            date_tag = content.find("li")
            if not date_tag: continue
            baslik_tag = content.find("h2")
            if not baslik_tag: continue

            dt = date_tag.get_text(strip=True)
            baslik = baslik_tag.get_text(strip=True)
            link = urljoin("https://www.santiye.com.tr", baslik_tag.find("a")["href"])

            # 1. Vitrindeki post-gallery görseli
            vitrin_img = ""
            parent_row = content.find_parent("div", class_="row")
            if parent_row:
                gal_img = parent_row.select_one(".post-gallery img")
                if gal_img and gal_img.get("src"):
                    vitrin_img = gal_img["src"]

            print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
            inner_r = requests.get(link, timeout=15, headers=HEADERS)
            inner_soup = BeautifulSoup(inner_r.content, "html.parser")

            # 2. İç sayfadaki görsel (reklamları elemek için haber gövdesinde arar)
            img_url = ""
            article_box = inner_soup.find("div", class_="article-post") or inner_soup.find("div", class_="block-content")
            if article_box:
                detay_img = article_box.find("img", class_="img-responsive")
                if detay_img and detay_img.get("src"):
                    img_url = detay_img["src"]

            if not img_url:
                img_url = vitrin_img

            if img_url:
                img_url = img_url.split("?")[0].strip()
                if not img_url.startswith("http"):
                    img_url = urljoin("https://www.santiye.com.tr", img_url)

            tam_metin = extract_clean_text(inner_r.content, '.post-content', is_santiye=True)
            safe_create({"haber_basligi": baslik, "gorsel": img_url, "haber_metni": tam_metin, "yayin_tarihi": format_date(dt), "portal": "Şantiye", "url": link})
            return
    except Exception as e: print(f"Hata: {e}")

def scrape_makina_market():
    print(f"\n--- Tarama: Makina Market ---")
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

            img_url = ""
            img_tag = inner_soup.select_one('.cs-entry__thumbnail img') or inner_soup.select_one('.entry-content img')
            if img_tag and img_tag.get("src"): img_url = img_tag["src"]

            tam_metin = extract_clean_text(inner_r.content, '.entry-content')
            safe_create({"haber_basligi": baslik, "gorsel": img_url, "haber_metni": tam_metin, "yayin_tarihi": format_date(dt), "portal": "Makina Market", "url": link})
            return
    except Exception as e: print(f"Hata: {e}")

def scrape_istif_mh():
    print(f"\n--- Tarama: İstif MH ---")
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

            img_url = ""
            img_tag = inner_soup.select_one('.kanews-article-thumbnail img') or inner_soup.select_one('.entry-content-inner img')
            if img_tag and img_tag.get("src"): img_url = img_tag["src"]

            tam_metin = extract_clean_text(inner_r.content, '.entry-content-inner')
            safe_create({"haber_basligi": baslik, "gorsel": img_url, "haber_metni": tam_metin, "yayin_tarihi": format_date(dt), "portal": "İstif MH", "url": link})
            return
    except Exception as e: print(f"Hata: {e}")

def scrape_newsplus_theme(base_url, portal_name):
    print(f"\n--- Tarama: {portal_name} ---")
    try:
        r = requests.get(base_url, timeout=15, headers=HEADERS)
        soup = BeautifulSoup(r.content, "html.parser")
        for art in soup.find_all("article"):
            time_tag = art.find("time")
            if not time_tag: continue
            dt = time_tag.get("datetime", "")
            title_tag = art.find("h2")
            if not title_tag: continue
            baslik = title_tag.get_text(strip=True); link = title_tag.find("a")["href"]

            print(f"   🔎 İçeriğe giriliyor: {baslik[:30]}...")
            inner_r = requests.get(link, timeout=15, headers=HEADERS)
            inner_soup = BeautifulSoup(inner_r.content, "html.parser")

            img_url = ""
            img_tag = inner_soup.select_one('.single-post-thumb img') or inner_soup.select_one('article img')
            if img_tag and img_tag.get("src"): img_url = img_tag["src"]

            tam_metin = extract_clean_text(inner_r.content, '.entry-content.articlebody')
            safe_create({"haber_basligi": baslik, "gorsel": img_url, "haber_metni": tam_metin, "yayin_tarihi": format_date(dt), "portal": portal_name, "url": link})
            return
    except Exception as e: print(f"Hata: {e}")

if __name__ == "__main__":
    print(f"📊 BAŞLIYORUZ! (SADECE 1'ER HABER)")
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

import os
import requests
from bs4 import BeautifulSoup
from pyairtable import Api
from dotenv import load_dotenv
from urllib.parse import urljoin, quote

load_dotenv()

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

# --- SİTE 1: FORUM MAKİNA ---
def scrape_forum_makina(ex_urls, ex_titles):
    print("\n🔍 [1/3] Forum Makina Taraması...")
    for page in range(1, 6):
        try:
            r = requests.get(f"https://www.forummakina.com.tr/tr/haberler?page={page}", timeout=20)
            soup = BeautifulSoup(r.content, "html.parser")
            for item in soup.find_all("li", class_="news"):
                date_div = item.find("div", class_="date")
                tarih = date_div.get_text(strip=True) if date_div else ""
                if "2026" in tarih:
                    title_div = item.find("div", class_="title")
                    baslik = title_div.get_text(strip=True) if title_div else ""
                    link_tag = item.find("a")
                    link = urljoin("https://www.forummakina.com.tr", link_tag["href"]) if link_tag else ""
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img_tag = item.find("img")
                    img = clean_img(img_tag["src"], "https://www.forummakina.com.tr") if img_tag else ""
                    metin = item.find("span").get_text(strip=True).replace("devamı", "") if item.find("span") else ""
                    table.create({"haber_basligi": baslik, "gorsel": [{"url": img}] if img else [], "haber_metni": metin, "portal": "Forum Makina", "url": link})
                    print(f"✅ Forum Makina: {baslik[:30]}...")
                    ex_urls.add(link.lower()); ex_titles.add(baslik.lower())
        except: break

# --- SİTE 2: LHT (LOJİSTİK HATTI) ---
def scrape_lht(ex_urls, ex_titles):
    print("\n🔍 [2/3] LHT Taraması...")
    for page in range(1, 4):
        url = f"https://www.lht.com.tr/kategori/haber/page/{page}/"
        try:
            r = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(r.content, "html.parser")
            for art in soup.find_all("article"):
                time_tag = art.find("time")
                dt = time_tag.get("datetime", "") if time_tag else ""
                if "2026" in dt:
                    title_tag = art.find("h2", class_="entry-title")
                    if not title_tag: continue
                    baslik = title_tag.get_text(strip=True)
                    link = title_tag.find("a")["href"]
                    if link.lower() in ex_urls or baslik.lower() in ex_titles: continue
                    img_tag = art.find("div", class_="post-thumb")
                    img_src = img_tag.find("img")["src"] if img_tag and img_

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
    """Airtable'daki mevcut URL ve Başlıkları çeker."""
    existing_urls = set()
    existing_titles = set()
    try:
        # Tüm kayıtları çekiyoruz
        records = table.all()
        for r in records:
            fields = r.get('fields', {})
            # URL'yi temizleyerek al (boşlukları sil, küçük harf yap)
            u = fields.get('url', '').strip().lower()
            if u: existing_urls.add(u)
            
            # Başlığı temizleyerek al
            t = fields.get('haber_basligi', '').strip().lower()
            if t: existing_titles.add(t)
            
        print(f"✅ Hafızaya Alındı: {len(existing_urls)} URL, {len(existing_titles)} Başlık.")
        return existing_urls, existing_titles
    except Exception as e:
        print(f"⚠️ Airtable verisi çekilemedi: {e}")
        return set(), set()

def clean_image_url(raw_url):
    if not raw_url: return ""
    url = raw_url.replace("http://", "https://")
    # Dosya ismindeki boşlukları %20 yapar
    parts = url.split("/")
    file_part = quote(parts[-1])
    return "/".join(parts[:-1]) + "/" + file_part

def scrape_forum_makina():
    # 1. Önce mevcut verileri hafızaya alıyoruz
    ex_urls, ex_titles = get_existing_data()
    print("🚀 Tarama başlatıldı...")

    # Sayfa 1'den 10'a kadar tara
    for page in range(1, 11): 
        url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        print(f"📄 Sayfa {page} taranıyor...")
        
        try:
            r = requests.get(url, timeout=20)
            soup = BeautifulSoup(r.content, "html.parser")
            news_items = soup.find_all("li", class_="news")
            
            if not news_items: break

            for item in news_items:
                # Tarih kontrolü
                date_div = item.find("div", class_="date")
                tarih = date_div.text.strip() if date_div else ""
                
                if "2026" in tarih:
                    title_div = item.find("div", class_="title")
                    baslik = title_div.text.strip() if title_div else ""
                    
                    link_tag = item.find("a")
                    link = urljoin("https://www.forummakina.com.tr", link_tag["href"]) if link_tag else ""
                    
                    # --- MÜKERRER KONTROLÜ (KRİTİK) ---
                    clean_link = link.strip().lower()
                    clean_baslik = baslik.strip().lower()

                    if clean_link in ex_urls or clean_baslik in ex_titles:
                        print(f"⏭️ Pas geçildi (Zaten var): {baslik[:30]}")
                        continue
                    # ---------------------------------

                    img_tag = item.find("img")
                    raw_img_url = img_tag.get("src") if img_tag else ""
                    final_img = clean_image_url(raw_img_url)

                    metin = item.find("span").text.replace("devamı", "").strip() if item.find("span") else ""

                    payload = {
                        "

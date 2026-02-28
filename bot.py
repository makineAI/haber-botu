import requests
from bs4 import BeautifulSoup
import os
import time

# HESAP BİLGİLERİN (ID'ler sabit kalıyor)
BASE_ID = "appC4JNkqLfVCEcna"
TABLE_ID = "tbl1paeNlwYfvKQlP"
TOKEN = os.environ.get('AIRTABLE_TOKEN')

def start():
    if not TOKEN:
        print("HATA: GitHub Secrets içinde AIRTABLE_TOKEN bulunamadı!")
        return

    # 1. Airtable'daki Mevcut Kayıtları Çek (Mükerrer Kontrolü için)
    existing_urls = set()
    try:
        # Airtable API varsayılan olarak 100 kayıt getirir, URL'leri hafızaya alıyoruz
        r = requests.get(f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}", 
                         headers={"Authorization": f"Bearer {TOKEN}"})
        if r.status_code == 200:
            for rec in r.json().get('records', []):
                u = rec.get('fields', {}).get('URL')
                if u: existing_urls.add(u)
        print(f"Bilgi: Airtable'da zaten {len(existing_urls)} haber kayıtlı.")
    except Exception as e:
        print(f"Mevcut kayıtlar okunurken hata (Geçiliyor): {e}")

    # 2. Siteyi Derinlemesine Tara
    new_records = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # 1. sayfadan 20. sayfaya kadar tara (Limitleri zorluyoruz)
    for p in range(1, 21): 
        url = f"https://www.forummakina.com.tr/tr/haberler?page={p}"
        print(f"Sayfa {p} taranıyor...")
        
        try:
            res = requests.get(url, headers=headers, timeout=20)
            if res.status_code != 200: break
            
            soup = BeautifulSoup(res.text, 'html.parser')
            date_divs = soup.find_all('div', class_='date')
            
            found_2026_on_page = 0
            for date_div in date_divs:
                # Sadece 2026 olanları yakala
                if "2026" in date_div.get_text(strip=True):
                    # Haberin ana kutusuna ulaş (Genelde col-md-4)
                    parent = date_div.find_parent('div', class_='col-md-4') or date_div.find_parent()
                    if parent:
                        link_tag = parent.find('a', href=True)
                        if link_tag:
                            href = link_tag['href']
                            full_link = "https://www.forummakina.com.tr" + href if not href.startswith('http') else href
                            
                            # DAHA ÖNCE EKLENMEMİŞSE AL
                            if full_link not in existing_urls:
                                title = link_tag.get_text(strip=True)
                                if len(title) < 20: # Kısa başlıkları (tarih vb) ele
                                    h3_tag = parent.find('h3')
                                    if h3_tag: title = h3_tag.get_text(strip=True)
                                
                                p_tag = parent.find('p')
                                desc = p_tag.get_text(strip=True) if p_tag else "Haber detayı içeride."

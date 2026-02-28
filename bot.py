import requests
from bs4 import BeautifulSoup
import os
import time

# AYARLAR
BASE_ID = "appC4JNkqLfVCEcna"
TABLE_ID = "tbl1paeNlwYfvKQlP"
TOKEN = os.environ.get('AIRTABLE_TOKEN')

def start():
    if not TOKEN:
        print("HATA: AIRTABLE_TOKEN bulunamadı!")
        return

    # 1. Mevcut Kayıtları Çek
    existing_urls = set()
    try:
        r = requests.get(f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}", 
                         headers={"Authorization": f"Bearer {TOKEN}"}, timeout=20)
        if r.status_code == 200:
            for rec in r.json().get('records', []):
                u = rec.get('fields', {}).get('URL')
                if u: existing_urls.add(u)
    except: pass

    # 2. Siteyi Tara
    new_records = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    for p in range(1, 11): # 10 sayfa tara
        url = f"https://www.forummakina.com.tr/tr/haberler?page={p}"
        print(f"Sayfa {p} inceleniyor...")
        
        try:
            res = requests.get(url, headers=headers, timeout=20)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Tüm haber bloklarını bul
            items = soup.find_all('div', class_='col-md-4')
            if not items: break
            
            found_count = 0
            for item in items:
                # 2026 Kontrolü
                if "2026" in item.get_text():
                    # BAŞLIK: Önce 'title' class'ına bak, yoksa h3'e bak, o da yoksa ilk linke bak
                    title_div = item.find('div', class_='title') or item.find('h3') or item.find('a')
                    # URL: Haber kutusundaki ilk geçerli link
                    link_tag = item.find('a', href=True)
                    # ÖN YAZI: Önce span'a bak, yoksa p'ye bak
                    desc_tag = item.find('span') or item.find('p')
                    
                    if title_div and link_tag:
                        href = link_tag['href']
                        full_link = "https://www.forummakina.com.tr" + href if not href.startswith('http') else href
                        
                        if full_link not in existing_urls:
                            title = title_div.get_text(strip=True)
                            # Eğer başlık "DEVAMI" gibi çok kısaysa kutudaki en uzun metni almayı dene
                            if len(title) < 10 and item.find('h3'):
                                title = item.find('h3').get_text(strip=True)
                                
                            desc = desc_tag.get_text(strip=True) if desc_tag else "Detay haberde."
                            
                            new_records.append({
                                "fields": {
                                    "Haber_Başlığı": title,
                                    "URL": full_link,
                                    "Haber_Ön_Yazı": desc
                                }
                            })
                            found_count += 1
            
            print(f"Sayfa {p}: {found_count} adet 2026 haberi listeye alındı.")
            if found_count == 0 and p > 1: break # 2026'lar bittiyse dur
            time.sleep(1)
            
        except Exception as e:
            print(f"Hata: {e}")
            break

    # 3. Gönderim
    if new_records:
        print(f"Toplam {len(new_records)} yeni haber Airtable'a gönderiliyor...")
        for i in range(0, len(new_records), 10):
            batch = new_records[i:i+10]
            requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}", 
                          json={"records": batch}, 
                          headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
        print("Bitti!")
    else:
        print("Eklenecek yeni haber bulunamadı.")

if __name__ == "__main__":
    start()

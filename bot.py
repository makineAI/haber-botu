import requests
from bs4 import BeautifulSoup
import os
import time

# SABİT AYARLAR
BASE_ID = "appC4JNkqLfVCEcna"
TABLE_ID = "tbl1paeNlwYfvKQlP"
TOKEN = os.environ.get('AIRTABLE_TOKEN')

def start():
    if not TOKEN:
        print("HATA: AIRTABLE_TOKEN bulunamadı!")
        return

    # 1. Airtable'daki mevcut kayıtları kontrol et (Mükerrer engelleme)
    existing_urls = set()
    try:
        r = requests.get(f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}", 
                         headers={"Authorization": f"Bearer {TOKEN}"}, timeout=20)
        if r.status_code == 200:
            for rec in r.json().get('records', []):
                u = rec.get('fields', {}).get('URL')
                if u: existing_urls.add(u)
        print(f"Bilgi: Airtable'da {len(existing_urls)} kayıt zaten var.")
    except:
        pass

    # 2. Siteyi tara (Sınırsız Sayfa Modu)
    new_records = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    for p in range(1, 21): # 20 sayfaya kadar tarar
        url = f"https://www.forummakina.com.tr/tr/haberler?page={p}"
        print(f"Sayfa {p} taranıyor...")
        
        try:
            res = requests.get(url, headers=headers, timeout=20)
            if res.status_code != 200: break
            
            soup = BeautifulSoup(res.text, 'html.parser')
            # Her bir haber kutusunu bul (col-md-4 yapısı)
            items = soup.find_all('div', class_='col-md-4')
            
            if not items: break # Sayfada hiç haber kutusu yoksa bitir
            
            found_2026 = 0
            for item in items:
                date_div = item.find('div', class_='date')
                # Sadece 2026 yazanları süz
                if date_div and "2026" in date_div.get_text(strip=True):
                    # BAŞLIK: <div class="title"> içinden
                    title_div = item.find('div', class_='title')
                    # URL: a etiketinden
                    link_tag = item.find('a', href=True)
                    # ÖN YAZI: span etiketinden
                    span_tag = item.find('span')
                    
                    if title_div and link_tag:
                        href = link_tag['href']
                        full_link = "https://www.forummakina.com.tr" + href if not href.startswith('http') else href
                        
                        # Eğer URL daha önce eklenmemişse listeye al
                        if full_link not in existing_urls:
                            title = title_div.get_text(strip=True)
                            desc = span_tag.get_text(strip=True) if span_tag else "Detaylar haber içeriğinde."
                            
                            new_records.append({
                                "fields": {
                                    "Haber_Başlığı": title,
                                    "URL": full_link,
                                    "Haber_Ön_Yazı": desc
                                }
                            })
                            found_2026 += 1
            
            print(f"Sayfa {p}: {found_2026} yeni haber yakalandı.")
            # Eğer bir sayfada 2026 kalmadıysa aramayı durdur (Eski yıllara geçilmiştir)
            if found_2026 == 0 and p > 1: break
            time.sleep(1)
            
        except Exception as e:
            print(f"Hata oluştu: {e}")
            break

    # 3. Airtable'a Gönder
    if new_records:
        print(f"Toplam {len(new_records)} yeni haber gönderiliyor...")
        api_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
        for i in range(0, len(new_records), 10):
            batch = new_records[i:i+10]
            requests.post(api_url, json={"records": batch}, 
                          headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
        print("İşlem başarıyla tamamlandı.")
    else:
        print("Yeni 2026 haberi bulunamadı.")

if __name__ == "__main__":
    start()

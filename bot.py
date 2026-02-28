import requests
from bs4 import BeautifulSoup
import os

# SABİT BİLGİLER
BASE_ID = "appC4JNkqLfVCEcna"
TABLE_ID = "tbl1paeNlwYfvKQlP"
TOKEN = os.environ.get('AIRTABLE_TOKEN')

def start():
    if not TOKEN:
        print("HATA: GitHub Secrets içinde AIRTABLE_TOKEN bulunamadı!")
        return

    # 1. Mevcut URL'leri çek (Mükerrer kontrolü)
    existing_urls = set()
    try:
        r = requests.get(f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}", 
                         headers={"Authorization": f"Bearer {TOKEN}"})
        if r.status_code == 200:
            for rec in r.json().get('records', []):
                u = rec.get('fields', {}).get('URL')
                if u: existing_urls.add(u)
    except: pass

    # 2. Siteyi tara
    new_records = []
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for p in range(1, 4): # İlk 3 sayfaya bak
        res = requests.get(f"https://www.forummakina.com.tr/tr/haberler?page={p}", headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for date_div in soup.find_all('div', class_='date'):
            if date_div.get_text(strip=True) == "2026":
                parent = date_div.find_parent('div', class_='col-md-4') or date_div.find_parent()
                if parent:
                    link = parent.find('a', href=True)
                    if link:
                        full_link = "https://www.forummakina.com.tr" + link['href'] if not link['href'].startswith('http') else link['href']
                        
                        if full_link not in existing_urls:
                            title = link.get_text(strip=True)
                            p_tag = parent.find('p')
                            desc = p_tag.get_text(strip=True) if p_tag else "Detay içeride."
                            
                            new_records.append({
                                "fields": {
                                    "Haber_Başlığı": title,
                                    "URL": full_link,
                                    "Haber_Ön_Yazı": desc
                                }
                            })
        if len(new_records) > 20: break # Çok fazla yükleme yapma

    # 3. Airtable'a gönder
    if new_records:
        for i in range(0, len(new_records), 10):
            batch = new_records[i:i+10]
            requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}", 
                          json={"records": batch}, 
                          headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
        print(f"Başarılı! {len(new_records)} yeni haber eklendi.")
    else:
        print("Yeni haber yok.")

if __name__ == "__main__":
    start()

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

    # 1. Mevcut Kayıtları Hafızaya Al (Mükerrer Kontrolü)
    existing_urls = set()
    try:
        r = requests.get(f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}", 
                         headers={"Authorization": f"Bearer {TOKEN}"}, timeout=20)
        if r.status_code == 200:
            for rec in r.json().get('records', []):
                u = rec.get('fields', {}).get('URL')
                if u: existing_urls.add(u)
    except: pass

    # 2. Sayfa Sayfa Tarama
    new_records = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    for p in range(1, 11): # 10 sayfaya kadar tara
        url = f"https://www.forummakina.com.tr/tr/haberler?page={p}"
        print(f"Sayfa {p} didik didik ediliyor...")
        
        try:
            res = requests.get(url, headers=headers, timeout=20)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Sitedeki tüm 'a' (link) etiketlerini bul
            all_links = soup.find_all('a', href=True)
            
            found_on_page = 0
            for link in all_links:
                href = link['href']
                # Sadece haber detayına giden linklere odaklan
                if "/tr/haberler/" in href:
                    full_link = "https://www.forummakina.com.tr" + href if not href.startswith('http') else href
                    
                    # Eğer bu linki daha önce eklemediysek, tarihini kontrol et
                    if full_link not in existing_urls:
                        # Linkin içinde bulunduğu en yakın kapsayıcıyı (div) bul
                        parent = link.find_parent('div')
                        if parent and "2026" in parent.get_text():
                            # Başlık: title class'ı veya linkin içindeki metin
                            title_div = parent.find('div', class_='title')
                            title = title_div.get_text(strip=True) if title_div else link.get_text(strip=True)
                            
                            # Ön Yazı: span etiketini ara
                            span_tag = parent.find('span')
                            desc = span_tag.get_text(strip=True) if span_tag else "Özet haber içeriğinde."
                            
                            # Eğer başlık hala çok kısaysa veya boşsa alma
                            if len(title) > 15:
                                new_records.append({
                                    "fields": {
                                        "Haber_Başlığı": title,
                                        "URL": full_link,
                                        "Haber_Ön_Yazı": desc
                                    }
                                })
                                # Bu URL'yi mevcutlara ekle ki aynı sayfada tekrar bulmasın
                                existing_urls.add(full_link)
                                found_on_page += 1
            
            print(f"Sayfa {p}: {found_on_page} adet yeni 2026 haberi listeye eklendi.")
            if found_on_page == 0 and p > 1: break
            time.sleep(1)
            
        except Exception as e:
            print(f"Hata: {e}")
            break

    # 3. Airtable'a Gönder
    if new_records:
        print(f"Toplam {len(new_records)} haber Airtable'a paketleniyor...")
        for i in range(0, len(new_records), 10):
            batch = new_records[i:i+10]
            requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}", 
                          json={"records": batch}, 
                          headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
        print("Operasyon Başarılı!")
    else:
        print("Üzgünüm, kriterlere uygun yeni haber yakalanamadı.")

if __name__ == "__main__":
    start()

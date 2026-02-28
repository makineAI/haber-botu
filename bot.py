import requests
from bs4 import BeautifulSoup
import os
import time

# AYARLAR (Airtable Bilgilerin)
BASE_ID = "appC4JNkqLfVCEcna"
TABLE_ID = "tbl1paeNlwYfvKQlP"
TOKEN = os.environ.get('AIRTABLE_TOKEN')

def get_airtable_data():
    """Airtable'daki tüm mevcut URL'leri hafızaya alır (Mükerrer engelleme için)"""
    existing_urls = set()
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    offset = None
    
    while True:
        params = {"offset": offset} if offset else {}
        r = requests.get(url, headers=headers, params=params)
        data = r.json()
        for record in data.get('records', []):
            u = record.get('fields', {}).get('URL')
            if u: existing_urls.add(u)
        
        offset = data.get('offset')
        if not offset: break
    return existing_urls

def start():
    if not TOKEN:
        print("HATA: TOKEN Tanımlanmamış!")
        return

    # 1. Önce Airtable'da ne var ne yok bakıyoruz
    print("Mevcut kayıtlar kontrol ediliyor...")
    existing_urls = get_airtable_data()

    # 2. Sayfaları 1'den başlayarak tarıyoruz
    all_new_news = []
    page = 1
    headers = {"User-Agent": "Mozilla/5.0"}

    while True:
        target_url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        print(f"Sayfa {page} taranıyor: {target_url}")
        
        res = requests.get(target_url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Haber kutularını buluyoruz
        items = soup.find_all('div', class_='col-md-4')
        
        # Eğer sayfada hiç haber kutusu yoksa, sitenin sonuna gelmişizdir
        if not items:
            print("Sayfa bitti veya haber bulunamadı.")
            break
            
        found_2026_on_this_page = 0
        
        for item in items:
            # Sadece 2026 tarihli olanları süzüyoruz
            date_div = item.find('div', class_='date')
            if date_div and "2026" in date_div.get_text():
                
                link_tag = item.find('a', href=True)
                if link_tag:
                    href = link_tag['href']
                    full_link = "https://www.forummakina.com.tr" + href if not href.startswith('http') else href
                    
                    # KRİTİK: Eğer bu URL Airtable'da YOKSA ve şu anki listemizde YOKSA ekle
                    if full_link not in existing_urls:
                        title_div = item.find('div', class_='title')
                        span_tag = item.find('span')
                        
                        title = title_div.get_text(strip=True) if title_div else "Başlıksız Haber"
                        desc = span_tag.get_text(strip=True) if span_tag else "Detaylar haberde."
                        
                        all_new_news.append({
                            "fields": {
                                "Haber_Başlığı": title,
                                "URL": full_link,
                                "Haber_Ön_Yazı": desc
                            }
                        })
                        existing_urls.add(full_link) # Listeye ekle ki aynı çalışmada tekrar gelmesin
                        found_2026_on_this_page += 1

        print(f"Sayfa {page} bitti. {found_2026_on_this_page} adet yeni 2026 haberi alındı.")
        
        # Eğer bu sayfada hiç 2026 haberi bulamadıysak, eski yıllara geçmişizdir, taramayı bitiriyoruz.
        if found_2026_on_this_page == 0:
            print("Artık 2026 haberi kalmadı, işlem durduruluyor.")
            break
            
        page += 1 # Sonraki sayfaya geç
        time.sleep(1) # Siteyi yormamak için kısa bekleme

    # 3. Toplanan tüm yeni haberleri Airtable'a gönder
    if all_new_news:
        print(f"Toplam {len(all_new_news)} yeni haber Airtable'a yükleniyor...")
        for i in range(0, len(all_new_news), 10):
            batch = all_new_news[i:i+10]
            requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}", 
                          json={"records": batch}, 
                          headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
        print("Yükleme tamamlandı!")
    else:
        print("Eklenecek yeni haber bulunamadı.")

if __name__ == "__main__":
    start()

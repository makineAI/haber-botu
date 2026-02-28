import requests
from bs4 import BeautifulSoup
import os
import time

# AYARLAR
BASE_ID = "appC4JNkqLfVCEcna"
TABLE_ID = "tbl1paeNlwYfvKQlP"
TOKEN = os.environ.get('AIRTABLE_TOKEN')

def get_airtable_data():
    """Mevcut URL'leri çekerek mükerrer kayıtları engeller."""
    existing_urls = set()
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    offset = None
    try:
        while True:
            params = {"offset": offset} if offset else {}
            r = requests.get(url, headers=headers, params=params, timeout=20)
            data = r.json()
            for record in data.get('records', []):
                u = record.get('fields', {}).get('URL')
                if u: existing_urls.add(u)
            offset = data.get('offset')
            if not offset: break
    except Exception as e:
        print(f"Airtable verisi okunurken hata: {e}")
    return existing_urls

def start():
    if not TOKEN:
        print("HATA: AIRTABLE_TOKEN bulunamadı!")
        return

    print("Sistem başlatılıyor... Mevcut kayıtlar kontrol ediliyor.")
    existing_urls = get_airtable_data()

    all_new_news = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # Sayfaları 1'den başlayarak tara (2026 haberleri bitene kadar)
    page = 1
    while page <= 20:
        target_url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        print(f"Sayfa {page} taranıyor: {target_url}")
        
        try:
            res = requests.get(target_url, headers=headers, timeout=30)
            if res.status_code != 200: break
            
            soup = BeautifulSoup(res.text, 'html.parser')
            # Senin paylaştığın HTML yapısı: li class="news"
            news_items = soup.find_all('li', class_='news')
            
            if not news_items:
                print("Sayfada haber bulunamadı.")
                break
                
            found_2026_on_page = 0
            for item in news_items:
                # 1. TARİH KONTROLÜ
                date_div = item.find('div', class_='date')
                if date_div and "2026" in date_div.get_text():
                    
                    # 2. URL BULMA
                    link_tag = item.find('a', href=True)
                    if not link_tag: continue
                    
                    href = link_tag['href']
                    full_link = "https://www.forummakina.com.tr" + href if not href.startswith('http') else href
                    
                    # 3. MÜKERRER KONTROLÜ (Daha önce eklenmiş mi?)
                    if full_link not in existing_urls:
                        # BAŞLIK
                        title_div = item.find('div', class_='title')
                        title = title_div.get_text(strip=True) if title_div else "Başlıksız"
                        
                        # ÖN YAZI (span içindeki 'devamı' linkini temizleyerek)
                        span_tag = item.find('span')
                        if span_tag:
                            for a in span_tag.find_all('a'): a.decompose() # 'devamı' yazısını sil
                            desc = span_tag.get_text(strip=True)
                        else:
                            desc = "Özet haber detayında."
                        
                        # GÖRSEL URL (img tag'inden çekme)
                        img_tag = item.find('img')
                        img_url = ""
                        if img_tag and img_tag.has_attr('src'):
                            img_url = img_tag['src']
                            # Link yarım gelirse tamamla
                            if not img_url.startswith('http'):
                                img_url = "https://www.forummakina.com.tr" + img_url
                        
                        # VERİYİ HAZIRLA
                        fields = {
                            "Haber_Başlığı": title,
                            "URL": full_link,
                            "Haber_Ön_Yazı": desc
                        }
                        
                        # Eğer resim varsa Airtable Attachment formatında ekle
                        if img_url:
                            fields["Görsel"] = [{"url": img_url}]
                        
                        all_new_news.append({"fields": fields})
                        existing_urls.add(full_link)
                        found_2026_on_page += 1

            print(f"Sayfa {page} bitti. Bulunan yeni haber: {found_2026_on_page}")
            
            # Eğer sayfada hiç 2026 haberi kalmamışsa aramayı durdur
            page_text = soup.get_text()
            if "2026" not in page_text and page > 1:
                print("2026 haberlerinin sonuna gelindi.")
                break
                
            page += 1
            time.sleep(1) # Siteyi yormayalım

        except Exception as e:
            print(f"Hata: {e}")
            break

    # 4. TOPLU GÖNDERİM (Airtable'a 10'arlı paketler halinde)
    if all_new_news:
        print(f"Toplam {len(all_new_news)} haber yükleniyor...")
        api_url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
        for i in range(0, len(all_new_news), 10):
            batch = all_new_news[i:i+10]
            r = requests.post(api_url, json={"records": batch}, 
                              headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
            if r.status_code not in [200, 201]:
                print(f"Gönderim hatası: {r.text}")
        print("İşlem başarıyla tamamlandı!")
    else:
        print("Eklenecek yeni haber bulunamadı.")

if __name__ == "__main__":
    start()

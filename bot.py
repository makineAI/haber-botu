import requests
from bs4 import BeautifulSoup
import os
import time

# AYARLAR
BASE_ID = "appC4JNkqLfVCEcna"
TABLE_ID = "tbl1paeNlwYfvKQlP"
TOKEN = os.environ.get('AIRTABLE_TOKEN')

def get_airtable_data():
    """Mevcut URL'leri Airtable'dan çeker."""
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
    except: pass
    return existing_urls

def start():
    if not TOKEN:
        print("HATA: TOKEN Tanımlanmamış!")
        return

    print("Airtable verileri kontrol ediliyor...")
    existing_urls = get_airtable_data()

    all_new_news = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    # 1. Sayfadan başlayarak tara
    page = 1
    while page <= 20: # Maksimum 20 sayfa tara
        target_url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        print(f"Sayfa {page} taranıyor...")
        
        try:
            res = requests.get(target_url, headers=headers, timeout=30)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # HABER KUTULARINI BUL (Verdiğin koda göre: li.news)
            news_items = soup.find_all('li', class_='news')
            
            if not news_items:
                print("Sayfada haber kutusu bulunamadı, tarama bitiriliyor.")
                break
                
            found_2026_count = 0
            for item in news_items:
                # 1. TARİH KONTROLÜ
                date_div = item.find('div', class_='date')
                if date_div and "2026" in date_div.get_text():
                    
                    # 2. URL BULMA (İlk a etiketindeki link)
                    link_tag = item.find('a', href=True)
                    if not link_tag: continue
                    
                    href = link_tag['href']
                    full_link = "https://www.forummakina.com.tr" + href if not href.startswith('http') else href
                    
                    # 3. MÜKERRER KONTROLÜ
                    if full_link not in existing_urls:
                        # 4. BAŞLIK BULMA (div class="title")
                        title_div = item.find('div', class_='title')
                        title = title_div.get_text(strip=True) if title_div else "Başlık Yok"
                        
                        # 5. ÖN YAZI BULMA (span içindeki metin, 'devamı' linki hariç)
                        span_tag = item.find('span')
                        if span_tag:
                            # Span içindeki 'a' etiketini (devamı yazısını) temizleyelim
                            for a_tag in span_tag.find_all('a'):
                                a_tag.decompose()
                            desc = span_tag.get_text(strip=True)
                        else:
                            desc = "Özet bulunamadı."
                        
                        all_new_news.append({
                            "fields": {
                                "Haber_Başlığı": title,
                                "URL": full_link,
                                "Haber_Ön_Yazı": desc
                            }
                        })
                        existing_urls.add(full_link)
                        found_2026_count += 1

            print(f"Sayfa {page}: {found_2026_count} yeni haber bulundu.")
            
            # Eğer bu sayfada hiç 2026 haberi yoksa (veya hepsi mükerrerse bile 0 gelirse)
            # Ama garantici olmak için sayfada en az bir tane 2026 tarihli yazı olup olmadığına bakıyoruz.
            page_text = soup.get_text()
            if "2026" not in page_text and page > 1:
                print("Artık 2026 tarihli içerik bulunamadı, durduruluyor.")
                break
                
            page += 1
            time.sleep(1)

        except Exception as e:
            print(f"Hata: {e}")
            break

    # Airtable'a gönder
    if all_new_news:
        print(f"Toplam {len(all_new_news)} haber Airtable'a yükleniyor...")
        for i in range(0, len(all_new_news), 10):
            batch = all_new_news[i:i+10]
            requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}", 
                          json={"records": batch}, 
                          headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
        print("Bitti! Tüm haberler başarıyla eklendi.")
    else:
        print("Yeni haber bulunamadı.")

if __name__ == "__main__":
    start()

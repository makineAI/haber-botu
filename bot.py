import requests
from bs4 import BeautifulSoup
import os
import time

# AYARLAR
BASE_ID = "appC4JNkqLfVCEcna"
TABLE_ID = "tbl1paeNlwYfvKQlP"
TOKEN = os.environ.get('AIRTABLE_TOKEN')

def get_airtable_data():
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

    print("Mevcut veriler taranıyor...")
    existing_urls = get_airtable_data()

    all_new_news = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    page = 1
    while page <= 15:
        target_url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        print(f"Sayfa {page} taranıyor...")
        
        try:
            res = requests.get(target_url, headers=headers, timeout=30)
            soup = BeautifulSoup(res.text, 'html.parser')
            news_items = soup.find_all('li', class_='news')
            
            if not news_items: break
                
            found_on_page = 0
            for item in news_items:
                date_div = item.find('div', class_='date')
                if date_div and "2026" in date_div.get_text():
                    link_tag = item.find('a', href=True)
                    if not link_tag: continue
                    
                    href = link_tag['href']
                    full_link = "https://www.forummakina.com.tr" + href if not href.startswith('http') else href
                    
                    if full_link not in existing_urls:
                        title_div = item.find('div', class_='title')
                        title = title_div.get_text(strip=True) if title_div else "Başlık Yok"
                        
                        # --- RESİM ÇEKME KISMI ---
                        img_tag = item.find('img')
                        img_url = img_tag['src'] if img_tag and img_tag.has_attr('src') else ""
                        # Eğer resim linki eksik gelirse tamamlayalım
                        if img_url and not img_url.startswith('http'):
                            img_url = "https://www.forummakina.com.tr" + img_url
                        
                        span_tag = item.find('span')
                        if span_tag:
                            for a_tag in span_tag.find_all('a'): a_tag.decompose()
                            desc = span_tag.get_text(strip=True)
                        else: desc = "Özet yok."
                        
                        all_new_news.append({
                            "fields": {
                                "Haber_Başlığı": title,
                                "URL": full_link,
                                "Haber_Ön_Yazı": desc,
                                "Görsel": img_url  # Resim linkini buraya ekledik
                            }
                        })
                        existing_urls.add(full_link)
                        found_on_page += 1

            if found_on_page == 0 and page > 1: break
            page += 1
            time.sleep(1)

        except Exception as e:
            print(f"Hata: {e}")
            break

    if all_new_news:
        print(f"Toplam {len(all_new_news)} haber (resimleriyle beraber) yükleniyor...")
        for i in range(0, len(all_new_news), 10):
            batch = all_new_news[i:i+10]
            requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}", 
                          json={"records": batch}, 
                          headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
        print("Görsel destekli yükleme tamamlandı!")
    else:
        print("Yeni haber yok.")

if __name__ == "__main__":
    start()

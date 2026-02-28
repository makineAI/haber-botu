import requests
from bs4 import BeautifulSoup
import os
import time

# AYARLARIN
TABLE_NAME = "MAI_Radar" 
AIRTABLE_TOKEN = os.environ['AIRTABLE_TOKEN']
AIRTABLE_BASE_ID = os.environ['AIRTABLE_BASE_ID']

def get_news():
    base_url = "https://www.forummakina.com.tr/tr/haberler?page="
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    all_valid_news = []
    page = 1
    keep_searching = True

    print("2026 Haberleri taranıyor...")

    while keep_searching:
        url = f"{base_url}{page}"
        print(f"Sayfa {page} kontrol ediliyor: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=20)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Sitedeki haber kutularını bul (Haberler genellikle 'col-md-4' veya 'news-item' içindedir)
            articles = soup.select('.news-card, .news-item, .col-md-4') # Genel seçiciler
            
            if not articles:
                print("Daha fazla haber bulunamadı veya sayfa sonuna gelindi.")
                break

            found_in_page = 0
            for item in articles:
                title_tag = item.find('h3') or item.find('h2')
                link_tag = item.find('a', href=True)
                date_tag = item.find(class_='date') or item.find('span') # Tarih alanı

                if title_tag and link_tag:
                    title = title_tag.get_text(strip=True)
                    link = "https://www.forummakina.com.tr" + link_tag['href'] if not link_tag['href'].startswith('http') else link_tag['href']
                    date_text = date_tag.get_text(strip=True) if date_tag else ""

                    # 2026 Kontrolü (Tarih metni içinde 2026 geçiyor mu?)
                    if "2026" in date_text:
                        all_valid_news.append({
                            "fields": {
                                "Haber_Metni": title,
                                "URL": link
                            }
                        })
                        found_in_page += 1
                    elif any(old_year in date_text for old_year in ["2025", "2024", "2023"]):
                        # Eğer 2025 veya daha eski bir tarih gördüysek, aramayı durdur
                        print(f"Eski tarih bulundu ({date_text}), tarama sonlandırılıyor.")
                        keep_searching = False
                        break
            
            print(f"Bu sayfada {found_in_page} adet 2026 haberi bulundu.")
            
            # Eğer sayfada hiç 2026 haberi yoksa ve biz hala devam ediyorsak, 
            # bazen tarih yazmıyor olabilir, birkaç sayfa daha bakıp emin olalım.
            if found_in_page == 0 and page > 3: 
                break

            page += 1
            time.sleep(1) # Siteyi yormamak için 1 saniye bekle

        except Exception as e:
            print(f"Hata: {e}")
            break

    # Aynı haberleri temizle
    unique_news = {v['fields']['Haber_Metni']: v for v in all_valid_news}.values()
    return list(unique_news)

def send_to_airtable(data):
    endpoint = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{TABLE_NAME}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    
    for i in range(0, len(data), 10):
        batch = data[i:i+10]
        requests.post(endpoint, json={"records": batch}, headers=headers)
        print(f"{len(batch)} haber Airtable'a eklendi.")

if __name__ == "__main__":
    results = get_news()
    if results:
        send_to_airtable(results)
    else:
        print("Kriterlere uygun (2026) haber bulunamadı.")

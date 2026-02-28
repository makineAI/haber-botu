import requests
from bs4 import BeautifulSoup
import os
import time

# SENİN HESAP BİLGİLERİN
BASE_ID = "appC4JNkqLfVCEcna"
TABLE_ID = "tbl1paeNlwYfvKQlP"
AIRTABLE_TOKEN = os.environ['AIRTABLE_TOKEN']

def get_news():
    base_url = "https://www.forummakina.com.tr/tr/haberler?page="
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    }
    
    all_valid_news = []
    page = 1
    keep_searching = True

    print("--- 2026 Haberleri Taranıyor ---")

    while keep_searching and page <= 10: # İlk 10 sayfaya kadar bakabilir
        url = f"{base_url}{page}"
        print(f"Sayfa {page} taranıyor...")
        
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code != 200:
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Sitedeki haber kartlarını bul (col-md-4 genellikle haber kutusudur)
            articles = soup.find_all('div', class_='col-md-4')
            
            if not articles:
                print("Haber kutusu bulunamadı, tarama durduruluyor.")
                break

            found_on_page = 0
            for item in articles:
                # 1. Başlık ve Link
                title_tag = item.find('h3')
                link_tag = item.find('a', href=True)
                # 2. Ön Yazı (Kısa özet)
                desc_tag = item.find('p') or item.find('div', class_='description')
                # 3. Tarih (2026 kontrolü için)
                date_tag = item.find('span', class_='date') or item.text

                if title_tag and link_tag:
                    title = title_tag.get_text(strip=True)
                    link = "https://www.forummakina.com.tr" + link_tag['href'] if not link_tag['href'].startswith('http') else link_tag['href']
                    description = desc_tag.get_text(strip=True) if desc_tag else "Özet bulunamadı."
                    full_text = item.get_text() # Tarih kontrolü için tüm kutu metnine bak

                    # 2026 Yılı Kontrolü
                    if "2026" in full_text:
                        all_valid_news.append({
                            "fields": {
                                "Haber_Başlığı": title,
                                "URL": link,
                                "Haber_Ön_Yazı": description
                            }
                        })
                        found_on_page += 1
                    elif any(old_year in full_text for old_year in ["2025", "2024", "2023"]):
                        # Eğer 2025 veya daha eski bir tarih gördüysek aramayı durdurabiliriz
                        print(f"Eski tarihli habere ulaşıldı, 2026 taraması bitti.")
                        keep_searching = False
                        break
            
            print(f"Sayfa {page}: {found_on_page} adet 2026 haberi alındı.")
            
            if found_on_page == 0 and page > 1: # İlk sayfada yoksa belki henüz girilmemiştir, ama sonraki sayfalarda hiç yoksa bitir
                break

            page += 1
            time.sleep(1) # Siteyi yormamak için

        except Exception as e:
            print(f"Hata: {e}")
            break

    # Mükerrerleri temizle
    unique_news = {v['fields']['Haber_Başlığı']: v for v in all_valid_news}.values()
    return list(unique_news)

def send_to_airtable(data):
    endpoint = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    for i in range(0, len(data), 10):
        batch = data[i:i+10]
        response = requests.post(endpoint, json={"records": batch}, headers=headers)
        if response.status_code in [200, 201]:
            print(f"{len(batch)} haber başarıyla Airtable'a yazıldı.")
        else:
            print(f"Hata: {response.text}")

if __name__ == "__main__":
    results = get_news()
    if results:
        send_to_airtable(results)
        print(f"İşlem tamam! Toplam {len(results)} haber gönderildi.")
    else:
        print("Kriterlere uygun (2026) yeni haber bulunamadı.")

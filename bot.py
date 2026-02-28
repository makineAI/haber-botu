import requests
from bs4 import BeautifulSoup
import os
import time

# AYARLARIN
TABLE_NAME = "MAI_Radar" 
AIRTABLE_TOKEN = os.environ['AIRTABLE_TOKEN']
AIRTABLE_BASE_ID = os.environ['AIRTABLE_BASE_ID']

def get_news():
    # Haberler sayfasının kök adresi
    base_url = "https://www.forummakina.com.tr/tr/haberler?page="
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    }
    
    all_news = []
    # Şimdilik test için ilk 3 sayfayı tarayalım (Sayıyı artırabilirsin)
    for page in range(1, 4): 
        url = f"{base_url}{page}"
        print(f"Sayfa {page} taranıyor: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code != 200:
                print(f"Sayfa açılamadı, hata kodu: {response.status_code}")
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Sitedeki tüm linkleri bul
            links = soup.find_all('a', href=True)
            page_found = 0
            
            for link in links:
                title = link.get_text(strip=True)
                href = link['href']
                
                # FİLTRE: Başlık en az 30 karakter olsun (Menü linklerini elemek için)
                # Ve linkin içinde "/haber/" veya benzeri bir yapı geçsin
                if len(title) > 30 and ("/haber/" in href or "/tr/" in href):
                    full_link = "https://www.forummakina.com.tr" + href if not href.startswith('http') else href
                    
                    all_news.append({
                        "fields": {
                            "Haber_Metni": title,
                            "URL": full_link
                        }
                    })
                    page_found += 1
            
            print(f"Sayfa {page} bitti. {page_found} potansiyel haber bulundu.")
            time.sleep(1) # Siteyi yormamak için kısa mola
            
        except Exception as e:
            print(f"Sayfa {page} taranırken hata: {e}")
            break

    # Aynı başlığa sahip mükerrer kayıtları temizle
    unique_news = {v['fields']['Haber_Metni']: v for v in all_news}.values()
    print(f"TOPLAM: {len(unique_news)} benzersiz haber/link bulundu.")
    return list(unique_news)

def send_to_airtable(data):
    endpoint = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    for i in range(0, len(data), 10):
        batch = data[i:i+10]
        response = requests.post(endpoint, json={"records": batch}, headers=headers)
        if response.status_code in [200, 201]:
            print(f"{len(batch)} kayıt başarıyla Airtable'a iletildi.")
        else:
            print(f"Airtable Hatası: {response.text}")

if __name__ == "__main__":
    results = get_news()
    if results:
        send_to_airtable(results)
    else:
        print("Siteden veri çekilemedi. Seçicileri (Selectors) kontrol etmek gerekebilir.")

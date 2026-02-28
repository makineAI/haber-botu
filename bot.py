import requests
from bs4 import BeautifulSoup
import os

# SENİN YENİ AYARLARIN
TABLE_NAME = "MAI_Radar" 
AIRTABLE_TOKEN = os.environ['AIRTABLE_TOKEN']
AIRTABLE_BASE_ID = os.environ['AIRTABLE_BASE_ID']

def get_news():
    url = "https://www.tasimacilar.com/haberler"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        news_list = []
        # Sitedeki haber başlıklarını tarar
        articles = soup.find_all('h2', class_='entry-title')
        print(f"Sitede {len(articles)} adet haber bulundu.")
        
        for article in articles:
            title_element = article.find('a')
            if title_element:
                title = title_element.get_text(strip=True)
                link = title_element['href']
                
                # SÜTUN İSİMLERİ BURADA (Haber_Metni ve URL)
                news_list.append({
                    "fields": {
                        "Haber_Metni": title,
                        "URL": link
                    }
                })
        return news_list
    except Exception as e:
        print(f"Hata oluştu: {e}")
        return []

def send_to_airtable(data):
    endpoint = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json"
    }
    
    for i in range(0, len(data), 10):
        batch = data[i:i+10]
        try:
            response = requests.post(endpoint, json={"records": batch}, headers=headers)
            if response.status_code in [200, 201]:
                print(f"{len(batch)} adet haber Airtable'a gönderildi.")
            else:
                print(f"Airtable Hatası ({response.status_code}): {response.text}")
        except Exception as e:
            print(f"Gönderim sırasında teknik hata: {e}")

if __name__ == "__main__":
    results = get_news()
    if results:
        send_to_airtable(results)
    else:
        print("Gönderilecek veri bulunamadı.")

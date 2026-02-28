import requests
from bs4 import BeautifulSoup
import os

# Ayarlar
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
        for article in soup.find_all('h2', class_='entry-title'):
            title_element = article.find('a')
            if title_element:
                title = title_element.get_text(strip=True)
                link = title_element['href']
                
                # SÜTUN İSİMLERİ BURADA EŞLEŞİYOR
                news_list.append({
                    "fields": {
                        "Haber_Metni": title, # Senin tablodaki isim
                        "URL": link           # Senin tablodaki isim
                    }
                })
        return news_list
    except Exception as e:
        print(f"Hata: {e}")
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
            print(f"Gönderim Durumu: {response.status_code}")
        except Exception as e:
            print(f"Airtable Hatası: {e}")

if __name__ == "__main__":
    results = get_news()
    if results:
        send_to_airtable(results)
    else:
        print("Haber bulunamadı.")

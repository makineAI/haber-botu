import requests
from bs4 import BeautifulSoup
import os

# AYARLAR
TABLE_NAME = "MAI_Radar" 
AIRTABLE_TOKEN = os.environ['AIRTABLE_TOKEN']
AIRTABLE_BASE_ID = os.environ['AIRTABLE_BASE_ID']

def debug_scrape():
    url = "https://www.forummakina.com.tr/tr/haberler"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    print(f"--- SİTE TARANIYOR: {url} ---")
    response = requests.get(url, headers=headers)
    print(f"Sitenin Yanıt Kodu: {response.status_code}") # 200 olmalı
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Sitedeki TÜM linkleri ve metinleri çekip ekrana yazdıralım
    links = soup.find_all('a', href=True)
    print(f"Sayfada toplam {len(links)} adet link bulundu.")
    
    found_data = []
    for link in links[:20]: # İlk 20 linki kontrol edelim
        text = link.get_text(strip=True)
        href = link['href']
        if len(text) > 10: # Çok kısa olmayanları yazdır
            print(f"Bulunan Potansiyel Haber: {text} | Link: {href}")
            found_data.append({"fields": {"Haber_Metni": text, "URL": "https://www.forummakina.com.tr" + href}})

    return found_data

def test_airtable(data):
    print(f"--- AIRTABLE TESTİ BAŞLIYOR ({len(data)} kayıt için) ---")
    endpoint = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{TABLE_NAME}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    
    if not data:
        print("Gönderilecek veri yok, Airtable testi atlanıyor.")
        return

    test_payload = {"records": data[:3]} # Sadece ilk 3 tanesini dene
    response = requests.post(endpoint, json=test_payload, headers=headers)
    
    print(f"Airtable Yanıtı: {response.status_code}")
    print(f"Airtable Mesajı: {response.text}") # Hata varsa burada yazar

if __name__ == "__main__":
    results = debug_scrape()
    test_airtable(results)

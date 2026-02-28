import requests
from bs4 import BeautifulSoup
import os
import time

# HESAP BİLGİLERİN
BASE_ID = "appC4JNkqLfVCEcna"
TABLE_ID = "tbl1paeNlwYfvKQlP"
AIRTABLE_TOKEN = os.environ['AIRTABLE_TOKEN']

def get_news():
    url = "https://www.forummakina.com.tr/tr/haberler"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    }
    
    all_news = []
    print(f"--- Güncel Haberler Taranıyor: {url} ---")
    
    try:
        response = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Sitedeki her bir haber bloğunu bulalım
        # Forum Makina'da haberler genellikle 'news-box' veya benzeri div'ler içindedir
        # En garanti yol: Tüm linkleri bulup içinden 'haber' geçenleri süzmek
        items = soup.find_all('a', href=True)
        
        for item in items:
            href = item['href']
            # Sadece haber linklerine odaklan (Linkin içinde /haber/ veya benzeri bir yapı varsa)
            if "/haber/" in href or "/tr/" in href:
                title = item.get_text(strip=True)
                
                # Başlık çok kısaysa (Örn: "Devamı", "Tümü") geç
                if len(title) < 30: 
                    continue
                
                full_link = "https://www.forummakina.com.tr" + href if not href.startswith('http') else href
                
                # Ön yazı için linkin çevresindeki paragrafa bakalım
                parent = item.find_parent()
                description = "Haber detayı için tıklayınız."
                if parent:
                    p_tag = parent.find_next_sibling('p') or parent.find('p')
                    if p_tag:
                        description = p_tag.get_text(strip=True)[:150] + "..."

                all_news.append({
                    "fields": {
                        "Haber_Başlığı": title,
                        "URL": full_link,
                        "Haber_Ön_Yazı": description
                    }
                })

        # Mükerrerleri temizle
        unique_news = {v['fields']['Haber_Başlığı']: v for v in all_news}.values()
        # Sadece en güncel 15 tanesini al (Test için)
        final_list = list(unique_news)[:15]
        print(f"Toplam {len(final_list)} adet güncel haber yakalandı.")
        return final_list

    except Exception as e:
        print(f"Hata: {e}")
        return []

def send_to_airtable(data):
    endpoint = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    
    for i in range(0, len(data), 10):
        batch = data[i:i+10]
        res = requests.post(endpoint, json={"records": batch}, headers=headers)
        if res.status_code in [200, 201]:
            print(f"{len(batch)} haber başarıyla Airtable'a uçtu!")
        else:
            print(f"Airtable Hatası: {res.text}")

if __name__ == "__main__":
    results = get_news()
    if results:
        send_to_airtable(results)
    else:
        print("Haber bulunamadı. Site yapısı değişmiş olabilir.")

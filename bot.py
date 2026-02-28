import requests
from bs4 import BeautifulSoup
import os
import time

# HESAP BİLGİLERİN
BASE_ID = "appC4JNkqLfVCEcna"
TABLE_ID = "tbl1paeNlwYfvKQlP"
AIRTABLE_TOKEN = os.environ.get('AIRTABLE_TOKEN')

def get_existing_urls():
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    existing_urls = set()
    try:
        response = requests.get(url, headers=headers, timeout=20)
        if response.status_code == 200:
            records = response.json().get('records', [])
            for record in records:
                u = record.get('fields', {}).get('URL')
                if u: existing_urls.add(u)
    except:
        pass
    return existing_urls

def get_news(existing_urls):
    headers = {"User-Agent": "Mozilla/5.0"}
    new_news = []
    
    for page in range(1, 6):
        url = f"https://www.forummakina.com.tr/tr/haberler?page={page}"
        try:
            res = requests.get(url, headers=headers, timeout=20)
            soup = BeautifulSoup(res.text, 'html.parser')
            date_divs = soup.find_all('div', class_='date')
            
            found_2026 = 0
            for date_div in date_divs:
                if date_div.get_text(strip=True) == "2026":
                    parent = date_div.find_parent('div', class_='col-md-4') or date_div.find_parent()
                    if parent:
                        link_tag = parent.find('a', href=True)
                        if link_tag:
                            title = link_tag.get_text(strip=True)
                            href = link_tag['href']
                            full_link = "https://www.forummakina.com.tr" + href if not href.startswith('http') else href
                            
                            # Kontroller: Başlık uzunluğu ve Mükerrer link
                            if len(title) > 20 and full_link not in existing_urls:
                                p_tag = parent.find('p')
                                desc = p_tag.get_text(strip=True) if p_tag else "Haber detayı içeride."
                                new_news.append({
                                    "fields": {
                                        "Haber_Başlığı": title,
                                        "URL": full_link,
                                        "Haber_Ön_Yazı": desc
                                    }
                                })
                                found_2026 += 1
            if found_2026 == 0 and page > 1: break
            time.sleep(1)
        except:
            break
    return new_news

if __name__ == "__main__":
    if not AIRTABLE_TOKEN:
        print("HATA: AIRTABLE_TOKEN bulunamadı!")
    else:
        existing = get_existing_urls()
        results = get_news(existing)
        if results:
            headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
            endpoint = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
            for i in range(0, len(results), 10):
                batch = results[i:i+10]
                requests.post(endpoint, json={"records": batch}, headers=headers)
            print(f"Bitti! {len(results)} yeni haber eklendi.")
        else:
            print("Eklenecek yeni haber yok.")

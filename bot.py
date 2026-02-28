import requests
from bs4 import BeautifulSoup
import os
import time

# HESAP BİLGİLERİN
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
    
    print("--- 2026 Haberleri Avı Başladı ---")

    while page <= 10: # İlk 10 sayfayı tara
        url = f"{base_url}{page}"
        print(f"Sayfa {page} taranıyor: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=20)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Sitedeki tüm linkleri (<a>) bul, çünkü başlıklar linkin içinde
            links = soup.find_all('a', href=True)
            
            found_on_page = 0
            for link in links:
                # Linkin içinde bulunduğu kapsayıcıyı (parent) al ki tarih ve özete bakalım
                parent = link.find_parent(['div', 'li', 'article'])
                if not parent: continue

                text_content = parent.get_text()
                
                # KRİTİK KONTROL: Metnin içinde "2026" geçiyor mu?
                if "2026" in text_content:
                    title = link.get_text(strip=True)
                    href = link['href']
                    
                    # Başlık çok kısaysa muhtemelen tarih veya buton linkidir, eleyelim
                    if len(title) < 20: continue

                    full_link = "https://www.forummakina.com.tr" + href if not href.startswith('http') else href
                    
                    # Ön yazı için parent içindeki p etiketine veya linkten sonraki metne bak
                    p_tag = parent.find('p')
                    description = p_tag.get_text(strip=True) if p_tag else "Özet haber içeriğinde."

                    all_valid_news.append({
                        "fields": {
                            "Haber_Başlığı": title,
                            "URL": full_link,
                            "Haber_Ön_Yazı": description
                        }
                    })
                    found_on_page += 1

            print(f"Sayfa {page}: {found_on_page} adet potansiyel 2026 haberi yakalandı.")
            
            # Eğer bu sayfada hiç 2026 bulamadıysak ve önceki sayfalarda bulduysak, bitmiş demektir
            if found_on_page == 0 and page > 1:
                print("Daha fazla 2026 haberi kalmadı.")
                break

            page += 1
            time.sleep(1)

        except Exception as e:
            print(f"Hata: {e}")
            break

    # Aynı başlıkları temizle (Farklı yerlerdeki aynı linkleri eler)
    unique_news = {v['fields']['Haber_Başlığı']: v for v in all_valid_news}.values()
    return list(unique_news)

def send_to_airtable(data):
    endpoint = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
    
    for i in range(0, len(data), 10):
        batch = data[i:i+10]
        requests.post(endpoint, json={"records": batch}, headers=headers)
        print(f"{len(batch)} haber Airtable'a gönderildi.")

if __name__ == "__main__":
    results = get_news()
    if results:
        send_to_airtable(results)
    else:
        print("Sitede '2026' ibaresi içeren haber bulunamadı. Lütfen siteyi kontrol et.")

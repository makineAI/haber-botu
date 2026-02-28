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
    
    all_2026_news = []
    page = 1
    
    print("--- 2026 Tarihli Haberler Aranıyor ---")

    while page <= 15: # İlk 15 sayfayı tara
        url = f"{base_url}{page}"
        print(f"Sayfa {page} taranıyor...")
        
        try:
            response = requests.get(url, headers=headers, timeout=20)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Sitedeki haber kartlarını bul (Genellikle col-md-4 içinde toplanır)
            # Ama biz senin verdiğin 'date' class'ı üzerinden gidelim
            date_divs = soup.find_all('div', class_='date')
            
            found_on_page = 0
            for date_div in date_divs:
                # Eğer div'in metni tam olarak 2026 ise
                if date_div.get_text(strip=True) == "2026":
                    # Bu div'in bağlı olduğu haber kartını bulalım (Parent)
                    parent = date_div.find_parent('div', class_='col-md-4') or date_div.find_parent()
                    
                    if parent:
                        title_tag = parent.find('h3') or parent.find('a')
                        link_tag = parent.find('a', href=True)
                        desc_tag = parent.find('p')
                        
                        if title_tag and link_tag:
                            title = title_tag.get_text(strip=True)
                            # Link bazen sadece h3 içinde bazen kartın genelinde olabilir
                            href = link_tag['href']
                            full_link = "https://www.forummakina.com.tr" + href if not href.startswith('http') else href
                            description = desc_tag.get_text(strip=True) if desc_tag else "Haber detayı içeride."

                            # Menü linklerini elemek için başlık uzunluk kontrolü
                            if len(title) > 20:
                                all_2026_news.append({
                                    "fields": {
                                        "Haber_Başlığı": title,
                                        "URL": full_link,
                                        "Haber_Ön_Yazı": description
                                    }
                                })
                                found_on_page += 1
            
            print(f"Sayfa {page}: {found_on_page} adet 2026 haberi bulundu.")
            
            # Eğer bu sayfada hiç 2026 yoksa ve birkaç sayfa geçildiyse bitir
            if found_on_page == 0 and page > 2:
                print("2026 haberleri bitti.")
                break

            page += 1
            time.sleep(1)

        except Exception as e:
            print(f"Hata: {e}")
            break

    # Mükerrerleri temizle
    unique_news = {v['fields']['Haber_Başlığı']: v for v in all_2026_news}.values()
    print(f"TOPLAM: {len(unique_news)} adet 2026 haberi hazır!")
    return list(unique_news)

def send_to_airtable(data):
    endpoint = f"

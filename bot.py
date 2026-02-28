import requests
from bs4 import BeautifulSoup
import os
import time

# HESAP BİLGİLERİN
BASE_ID = "appC4JNkqLfVCEcna"
TABLE_ID = "tbl1paeNlwYfvKQlP"
AIRTABLE_TOKEN = os.environ['AIRTABLE_TOKEN']

def get_existing_urls():
    """Airtable'da halihazırda bulunan haberlerin URL'lerini çeker."""
    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_ID}"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    params = {"fields[]": "URL"}
    
    existing_urls = set()
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            records = response.json().get('records', [])
            for record in records:
                url_val = record.get('fields', {}).get('URL')
                if url_val:
                    existing_urls.add(url_val)
        print(f"Bilgi: Airtable'da zaten kayıtlı olan {len(existing_urls)} adet haber bulundu.")
    except Exception as e:
        print(f"Mevcut kayıtlar kontrol edilirken hata oluştu: {e}")
    return existing_urls

def get_news(existing_urls):
    base_url = "https://www.forummakina.com.tr/tr/haberler?page="
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    }
    
    new_news = []
    page = 1
    
    print("

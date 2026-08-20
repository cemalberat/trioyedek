import requests
import json
import re
import xml.etree.ElementTree as ET

# SERPER API ANAHTARINI BURAYA YAPIŞTIR
SERPER_API_KEY = "73c1fd649f3af08c8a2f8aa786d479645a9898f0"

# İstenmeyen kelimeler (Ayakkabı, giyim, alakasız sektörler)
BLACKLIST = ["shoe", "shoes", "sneaker", "sneakers", "boot", "boots", "ayakkabı", 
             "nike", "adidas", "puma", "reebok", "apparel", "clothing", "shirt", "dress"]

def get_tcmb_rates():
    try:
        url = "https://www.tcmb.gov.tr/kurlar/today.xml"
        response = requests.get(url, timeout=5)
        tree = ET.fromstring(response.content)
        rates = {}
        for currency in tree.findall('Currency'):
            code = currency.get('Kod')
            if code in ['EUR', 'USD']:
                forex_selling = currency.find('ForexSelling').text
                rates[code] = float(forex_selling)
        return rates
    except Exception as e:
        print("⚠️ TCMB Hatası, yedek kurlar kullanılıyor:", e)
        return {'EUR': 38.50, 'USD': 35.20}

def optimize_part_code(code):
    return re.sub(r'(?i)(nt|tu|tr)$', '', str(code)).strip()

def search_europe_price(part_code):
    clean_code = optimize_part_code(part_code)
    
    print(f"\n🚀 AKILLI ARAMA BAŞLADI: {clean_code} (Sıfır/OEM Filtreli)")
    
    if SERPER_API_KEY == "BURAYA_SERPER_API_KEY_GELECEK":
        print("🚨 KOD DURDURULDU: Lütfen geçerli bir Serper API anahtarı girin!")
        return []

    rates = get_tcmb_rates()
    eur_rate = rates.get('EUR', 38.5)
    
    headers = {
      'X-API-KEY': SERPER_API_KEY,
      'Content-Type': 'application/json'
    }
    
    results_list = []
    seen_links = set()

    # ========================================================
    # 1. MOTOR: GOOGLE SHOPPING API
    # ========================================================
    print("🛒 1. Motor (Google Shopping) taranıyor...")
    try:
        shop_payload = json.dumps({"q": clean_code, "gl": "de", "hl": "en", "num": 50})
        res_shop = requests.post("https://google.serper.dev/shopping", headers=headers, data=shop_payload)
        
        if res_shop.status_code == 200:
            shopping_data = res_shop.json().get("shopping", [])
            
            for item in shopping_data:
                title = item.get("title", "").lower()
                link = item.get("link", "")
                price_str = item.get("price", "")
                source = item.get("source", "Avrupa Tedarikçisi")
                
                # İkinci el ve Kara Liste (Ayakkabı/Giyim) filtreleri
                if "used" in title or "second hand" in title or "refurbished" in title:
                    continue
                if any(bad_word in title for bad_word in BLACKLIST):
                    continue
                    
                clean_str = re.sub(r'[^\d.,]', '', price_str)
                if clean_str:
                    if ',' in clean_str and '.' in clean_str:
                        clean_str = clean_str.replace('.', '').replace(',', '.') if clean_str.rfind(',') > clean_str.rfind('.') else clean_str.replace(',', '')
                    elif ',' in clean_str:
                        clean_str = clean_str.replace(',', '.')
                    
                    try:
                        eur_val = float(clean_str)
                        if eur_val > 1 and link not in seen_links:
                            seen_links.add(link)
                            results_list.append({
                                "Parça Kodu": clean_code,
                                "Tedarikçi (Avrupa)": source + " (Mağaza)",
                                "Durum": "Sıfır / OEM",
                                "Fiyat (EUR)": round(eur_val, 2),
                                "Kur (TCMB)": round(eur_rate, 2),
                                "Fiyat (TL)": round(eur_val * eur_rate, 2),
                                "Satın Alma Linki": link
                            })
                    except:
                        pass
    except Exception as e:
        print("🚨 Shopping Motoru Hatası:", e)

    # ========================================================
    # 2. MOTOR: GOOGLE ORGANIC API
    # ========================================================
    print("🌐 2. Motor (Google Organik) taranıyor...")
    try:
        org_payload = json.dumps({"q": f'{clean_code} spare part OR laptop', "gl": "de", "hl": "en", "num": 50})
        res_org = requests.post("https://google.serper.dev/search", headers=headers, data=org_payload)
        
        if res_org.status_code == 200:
            organic_data = res_org.json().get("organic", [])
            
            for item in organic_data:
                title = item.get("title", "").lower()
                snippet = item.get("snippet", "") + " " + title
                link = item.get("link", "")
                
                if "used" in title or "second hand" in title or "refurbished" in title:
                    continue
                if any(bad_word in title for bad_word in BLACKLIST):
                    continue
                    
                price_matches = re.findall(r'(?:EUR|€|Euro)\s*\d+[.,\d]*|\d+[.,\d]*\s*(?:EUR|€|Euro)', snippet, re.IGNORECASE)
                
                if price_matches:
                    found_prices = []
                    for p_match in price_matches:
                        clean_str = re.sub(r'[^\d.,]', '', p_match)
                        if ',' in clean_str and '.' in clean_str:
                            clean_str = clean_str.replace('.', '').replace(',', '.') if clean_str.rfind(',') > clean_str.rfind('.') else clean_str.replace(',', '')
                        elif ',' in clean_str:
                            clean_str = clean_str.replace(',', '.')
                        try:
                            found_prices.append(float(clean_str))
                        except:
                            pass
                    
                    if found_prices:
                        # Kargo ücretlerine aldanmamak için Google'ın bulduğu fiyatlardan yüksek olanı asıl fiyat kabul et
                        eur_val = max(found_prices)
                        
                        if eur_val > 1 and link not in seen_links:
                            seen_links.add(link)
                            results_list.append({
                                "Parça Kodu": clean_code,
                                "Tedarikçi (Avrupa)": item.get("title", "")[:40] + "...",
                                "Durum": "Sıfır / OEM",
                                "Fiyat (EUR)": round(eur_val, 2),
                                "Kur (TCMB)": round(eur_rate, 2),
                                "Fiyat (TL)": round(eur_val * eur_rate, 2),
                                "Satın Alma Linki": link
                            })
    except Exception as e:
        print("🚨 Organik Motor Hatası:", e)
        
    print(f"🎯 FİLTRELEME BİTTİ! Ekrana basılan geçerli ürün sayısı: {len(results_list)}")
    return results_list
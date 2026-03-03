"""
Trendyol Scraper Servisi - Playwright ile JavaScript Desteği
"""
import logging
import re
import json
from typing import List, Dict, Optional
import time
import asyncio

logger = logging.getLogger(__name__)

class TrendyolScraper:
    """Trendyol mağazasından veri çeker"""
    
    def __init__(self, store_url: str, max_retries: int = 3, retry_delay: int = 5):
        self.store_url = store_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.browser = None
    
    def initialize(self) -> bool:
        """Scraper'ı başlat"""
        try:
            # Playwright'ı yükle
            try:
                from playwright.sync_api import sync_playwright
                logger.info("✅ Playwright bulundu")
            except ImportError:
                logger.warning("⚠️ Playwright yüklü değil, yüklüyorum...")
                import subprocess
                subprocess.check_call(['pip', 'install', 'playwright'])
                subprocess.check_call(['playwright', 'install', 'chromium'])
                from playwright.sync_api import sync_playwright
                logger.info("✅ Playwright yüklendi")
            
            return True
        except Exception as e:
            logger.error(f"❌ Scraper başlatma hatası: {e}")
            return False
    
    def fetch_products(self) -> List[Dict]:
        """Mağaza sayfasından ürünleri çek"""
        try:
            logger.info(f"🔍 Ürünler çekiliyor: {self.store_url}")
            
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # User-Agent ayarla
                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                # Sayfayı yükle
                page.goto(self.store_url, wait_until='domcontentloaded', timeout=60000)
                
                # JavaScript'in çalışması için bekle
                time.sleep(3)
                
                # Ürün linklerini bul - Trendyol ürünleri /lavazza/, /penti- vb. şeklinde
                product_elements = page.query_selector_all('a[href*="?boutiqueId="]')
                
                logger.info(f"📦 {len(product_elements)} ürün linki bulundu")
                
                products = []
                seen_ids = set()
                
                for elem in product_elements[:10]:  # İlk 10 ürün
                    try:
                        href = elem.get_attribute('href')
                        text = elem.text_content()
                        
                        if not href or not text:
                            continue
                        
                        # Tam URL'ye dönüştür
                        if href.startswith('/'):
                            href = 'https://www.trendyol.com' + href
                        
                        # Ürün ID'sini çıkar
                        if '?boutiqueId=' in href or 'merchantId=' in href:
                            # URL'den ürün ID'sini çıkar
                            product_id = href.split('/')[-1].split('?')[0] if '/' in href else href.split('?')[0]
                            
                            if product_id and product_id not in seen_ids:
                                product_name = text.strip()
                                
                                # Ürün adını temizle - "Hızlı Bakış" vb. metinleri kaldır
                                product_name = product_name.replace('Hızlı Bakış', '').replace('Yetkili Satıcı', '').replace('Başarılı Satıcı', '').strip()
                                
                                if product_name and len(product_name) > 3:
                                    products.append({
                                        'id': product_id,
                                        'name': product_name,
                                        'url': href
                                    })
                                    seen_ids.add(product_id)
                                    logger.info(f"  ✓ {product_name}")
                    except Exception as e:
                        logger.warning(f"⚠️ Ürün çekme hatası: {e}")
                        continue
                
                browser.close()
                
                logger.info(f"✅ {len(products)} benzersiz ürün çekildi")
                return products
        except Exception as e:
            logger.error(f"❌ Ürün çekme hatası: {e}")
            return []
    
    def fetch_sellers_for_product(self, product_url: str) -> List[Dict]:
        """Bir ürün için TÜM satıcıları çek"""
        try:
            logger.info(f"🔍 Satıcılar çekiliyor")
            
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # User-Agent ayarla
                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                # Sayfayı yükle
                page.goto(product_url, wait_until='domcontentloaded', timeout=60000)
                
                # JavaScript'in çalışması için bekle
                time.sleep(3)
                
                # Sayfadaki tüm metni al
                page_text = page.evaluate('() => document.body.innerText')
                page_source = page.content()
                
                sellers = []
                
                # JSON verilerini ara
                seller_data_list = self._extract_sellers_from_page(page_source, page_text)
                sellers.extend(seller_data_list)
                
                # Eğer JSON'dan bulunamazsa, DOM'dan çık
                if not sellers:
                    sellers = self._extract_sellers_from_text(page_text)
                
                browser.close()
                
                logger.info(f"✅ {len(sellers)} satıcı çekildi")
                return sellers
        except Exception as e:
            logger.error(f"❌ Satıcı çekme hatası: {e}")
            return []
    
    def _extract_sellers_from_page(self, page_source: str, page_text: str) -> List[Dict]:
        """Sayfadan tüm satıcıları dinamik olarak çıkar"""
        sellers = []
        
        try:
            # JSON verilerini ara
            json_patterns = [
                r'window\.__PRODUCT_DETAIL_APP_INITIAL_STATE__\s*=\s*({.*?});',
                r'"sellers"\s*:\s*\[({.*?})\]',
                r'<script[^>]*type="application/json"[^>]*>({.*?})</script>',
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, page_source, re.DOTALL)
                for match in matches:
                    try:
                        json_str = match
                        if not json_str.startswith('{'):
                            json_str = '{' + json_str
                        if not json_str.endswith('}'):
                            json_str = json_str + '}'
                        
                        data = json.loads(json_str)
                        if isinstance(data, dict):
                            sellers_data = self._extract_sellers_from_json(data)
                            sellers.extend(sellers_data)
                    except:
                        pass
            
            return sellers
        except Exception as e:
            logger.warning(f"⚠️ JSON satıcı çıkarma hatası: {e}")
            return []
    
    def _extract_sellers_from_text(self, page_text: str) -> List[Dict]:
        """Sayfa metninden satıcıları çıkar"""
        sellers = []
        
        try:
            # Satıcı adı + fiyat + rating kombinasyonlarını ara
            # Trendyol'da satıcılar şu şekilde görünüyor:
            # "Satıcı Adı
            #  Fiyat TL
            #  Rating (örn: 9.6)"
            
            lines = page_text.split('\n')
            
            for i, line in enumerate(lines):
                line_clean = line.strip()
                
                # Fiyat ve TL içeren satırları ara
                if 'TL' in line_clean and re.search(r'\d{1,5}[.,]\d{3}', line_clean):
                    try:
                        # Satıcı adını bul (genelde bir satır üstünde)
                        seller_name = None
                        price = None
                        rating = None
                        
                        # Mevcut satırdan fiyatı çıkar
                        price_match = re.search(r'(\d{1,5}[.,]\d{3})\s*TL', line_clean)
                        if price_match:
                            price_str = price_match.group(1).replace('.', '').replace(',', '.')
                            price = float(price_str)
                        
                        # Satıcı adını ara (bir satır üstünde)
                        if i > 0:
                            prev_line = lines[i-1].strip()
                            # Satıcı adı genelde sadece metin içerir (sayı değil)
                            if prev_line and not re.search(r'^\d', prev_line) and len(prev_line) > 2:
                                seller_name = prev_line
                        
                        # Rating'i ara (bir satır altında)
                        if i < len(lines) - 1:
                            next_line = lines[i+1].strip()
                            rating_match = re.search(r'^(\d[.,]\d)', next_line)
                            if rating_match:
                                rating_str = rating_match.group(1).replace(',', '.')
                                rating = float(rating_str)
                        
                        if seller_name and price and seller_name not in ['', 'Hızlı Bakış', 'Yetkili Satıcı', 'Başarılı Satıcı']:
                            seller = {
                                'name': seller_name,
                                'price': price,
                                'rating': rating if rating else 0.0,
                                'coupon': '',
                                'basket_discount': '',
                                'net_price': price
                            }
                            
                            # Duplikat kontrol
                            if not any(s['name'] == seller['name'] for s in sellers):
                                sellers.append(seller)
                                logger.info(f"  ✓ {seller_name} - {price} TL (Rating: {rating if rating else 'N/A'})")
                    except:
                        pass
            
            return sellers
        except Exception as e:
            logger.warning(f"⚠️ Metin satıcı çıkarma hatası: {e}")
            return []
    
    def _extract_sellers_from_json(self, data: dict) -> List[Dict]:
        """JSON'dan satıcıları çıkar"""
        sellers = []
        
        def find_sellers_recursive(obj, depth=0):
            if depth > 20:
                return
            
            if isinstance(obj, dict):
                if 'sellerName' in obj or ('name' in obj and 'price' in obj):
                    try:
                        seller_name = obj.get('sellerName') or obj.get('name', 'Bilinmiyor')
                        price = obj.get('price', 0)
                        
                        if isinstance(price, str):
                            price = float(re.sub(r'[^\d.,]', '', price).replace(',', '.'))
                        else:
                            price = float(price) if price else 0.0
                        
                        seller = {
                            'name': str(seller_name),
                            'price': price,
                            'rating': float(obj.get('rating', 0)) if obj.get('rating') else 0.0,
                            'coupon': str(obj.get('coupon', '')),
                            'basket_discount': str(obj.get('basketDiscount', '')),
                            'net_price': price
                        }
                        
                        if seller['name'] != 'Bilinmiyor' and seller['price'] > 0:
                            sellers.append(seller)
                    except:
                        pass
                
                for value in obj.values():
                    find_sellers_recursive(value, depth + 1)
            
            elif isinstance(obj, list):
                for item in obj:
                    find_sellers_recursive(item, depth + 1)
        
        find_sellers_recursive(data)
        return sellers
    
    def close(self) -> None:
        """Scraper'ı kapat"""
        logger.info("✅ Scraper kapatıldı")

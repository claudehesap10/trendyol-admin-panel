"""
Trendyol Scraper Servisi - Playwright ile JavaScript Desteği
Ürün sayfasındaki satıcı bilgilerini çeker (fiyat, kupon, indirim, rating)
"""
import logging
import re
import json
from typing import List, Dict, Optional
import time

logger = logging.getLogger(__name__)

class TrendyolScraper:
    """Trendyol mağazasından veri çeker"""
    
    def __init__(self, store_url: str, max_retries: int = 3, retry_delay: int = 5):
        self.store_url = store_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def initialize(self) -> bool:
        """Scraper'ı başlat"""
        try:
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
                
                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                page.goto(self.store_url, wait_until='domcontentloaded', timeout=60000)
                time.sleep(3)
                
                # Ürün linklerini bul
                product_elements = page.query_selector_all('a[href*="?boutiqueId="]')
                
                logger.info(f"📦 {len(product_elements)} ürün linki bulundu")
                
                products = []
                seen_ids = set()
                
                for elem in product_elements[:10]:
                    try:
                        href = elem.get_attribute('href')
                        text = elem.text_content()
                        
                        if not href or not text:
                            continue
                        
                        if href.startswith('/'):
                            href = 'https://www.trendyol.com' + href
                        
                        if '?boutiqueId=' in href or 'merchantId=' in href:
                            product_id = href.split('/')[-1].split('?')[0] if '/' in href else href.split('?')[0]
                            
                            if product_id and product_id not in seen_ids:
                                product_name = text.strip()
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
    
    def fetch_sellers_for_product(self, product_url: str, product_name: str = "") -> List[Dict]:
        """Bir ürün için satıcıları çek"""
        try:
            logger.info(f"🔍 Satıcılar çekiliyor")
            
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                page.goto(product_url, wait_until='domcontentloaded', timeout=60000)
                time.sleep(3)
                
                # Sayfadaki metni al
                page_text = page.evaluate('() => document.body.innerText')
                page_source = page.content()
                
                sellers = []
                
                # Sayfadaki satıcı bilgilerini parse et
                sellers = self._extract_sellers_from_page(page_text, page_source, product_name)
                
                browser.close()
                
                logger.info(f"✅ {len(sellers)} satıcı çekildi")
                return sellers
        except Exception as e:
            logger.error(f"❌ Satıcı çekme hatası: {e}")
            return []
    
    def _extract_sellers_from_page(self, page_text: str, page_source: str, product_name: str) -> List[Dict]:
        """Sayfadan satıcıları çıkar"""
        sellers = []
        
        try:
            # Sayfadaki fiyat bilgilerini ara
            # Format: "1.525 TL" veya "Sepette 1.512 TL"
            
            lines = page_text.split('\n')
            
            # Satıcı adını ara - genelde "Esvento" gibi bir isim
            seller_name = ""
            price = 0.0
            old_price = 0.0
            coupon = ""
            basket_discount = ""
            rating = 0.0
            
            for i, line in enumerate(lines):
                line_clean = line.strip()
                
                # Rating'i ara - "9.6" gibi
                if re.match(r'^\d[.,]\d$', line_clean):
                    try:
                        rating = float(line_clean.replace(',', '.'))
                    except:
                        pass
                
                # Kupon bilgisini ara - "%5 İndirimli Kupon!"
                if 'İndirimli Kupon' in line_clean or 'Kupon' in line_clean:
                    coupon_match = re.search(r'%(\d+)', line_clean)
                    if coupon_match:
                        coupon = f"%{coupon_match.group(1)} Kupon"
                
                # Sepette indirim - "Sepette %10 İndirim"
                if 'Sepette' in line_clean and '%' in line_clean:
                    basket_discount = line_clean
                
                # Fiyat bilgisini ara - "1.525 TL" veya "Sepette 1.512 TL"
                if 'TL' in line_clean and re.search(r'\d{1,5}[.,]\d{3}', line_clean):
                    price_match = re.search(r'(\d{1,5}[.,]\d{3})\s*TL', line_clean)
                    if price_match:
                        price_str = price_match.group(1).replace('.', '').replace(',', '.')
                        price = float(price_str)
                        
                        # Eski fiyat varsa bir satır üstünde
                        if i > 0:
                            prev_line = lines[i-1].strip()
                            if 'TL' in prev_line:
                                old_price_match = re.search(r'(\d{1,5}[.,]\d{3})\s*TL', prev_line)
                                if old_price_match:
                                    old_price_str = old_price_match.group(1).replace('.', '').replace(',', '.')
                                    old_price = float(old_price_str)
                
                # Satıcı adını ara - genelde bir satır fiyatın üstünde
                if price > 0 and not seller_name:
                    # Fiyat bulunduktan sonra satıcı adını ara
                    for j in range(max(0, i-5), i):
                        prev = lines[j].strip()
                        # Satıcı adı genelde sadece metin içerir, sayı değil
                        if prev and not re.search(r'^\d', prev) and len(prev) > 2 and len(prev) < 50:
                            if not any(x in prev for x in ['TL', '%', 'İndirim', 'Kupon', 'Sepette', 'Rating', 'Fiyat']):
                                seller_name = prev
                                break
            
            # Eğer satıcı adı bulunamadıysa, sayfadaki ilk satıcı adını ara
            if not seller_name:
                # "Esvento", "KAHVEDEBİZ" vb. satıcı adlarını ara
                seller_match = re.search(r'(Esvento|KAHVEDEBİZ|Mass Coffee|Lavazza|[A-Z][a-zÇçĞğİıÖöŞşÜü]+)', page_text)
                if seller_match:
                    seller_name = seller_match.group(1)
            
            # Net fiyatı hesapla (kupon ve sepette indirim uygulanmış)
            net_price = price
            if coupon and '%' in coupon:
                coupon_percent_match = re.search(r'%(\d+)', coupon)
                if coupon_percent_match:
                    coupon_percent = int(coupon_percent_match.group(1))
                    net_price = price * (1 - coupon_percent / 100)
            
            if seller_name and price > 0:
                seller = {
                    'product_name': product_name,
                    'name': seller_name,
                    'price': price,
                    'old_price': old_price,
                    'coupon': coupon,
                    'basket_discount': basket_discount,
                    'net_price': net_price,
                    'rating': rating
                }
                sellers.append(seller)
                logger.info(f"  ✓ {seller_name} - {price} TL")
            
            return sellers
        except Exception as e:
            logger.warning(f"⚠️ Satıcı çıkarma hatası: {e}")
            return []
    
    def close(self) -> None:
        """Scraper'ı kapat"""
        logger.info("✅ Scraper kapatıldı")

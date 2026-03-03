"""
Trendyol Scraper Servisi - Playwright ile JavaScript Desteği
"Ürünün Diğer Satıcıları" bölümünden tüm satıcıları çeker
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
                        
                        # URL'yi tam hale getir
                        if href.startswith('/'):
                            href = 'https://www.trendyol.com' + href
                        elif not href.startswith('http'):
                            href = 'https://www.trendyol.com/' + href
                        
                        if '?boutiqueId=' in href or 'merchantId=' in href or 'p-' in href:
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
        """Bir ürün için "Ürünün Diğer Satıcıları" bölümünden TÜM satıcıları çek"""
        try:
            logger.info(f"🔍 Satıcılar çekiliyor: {product_name}")
            
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                page.goto(product_url, wait_until='domcontentloaded', timeout=60000)
                time.sleep(3)
                
                sellers = []
                
                # Ürün adını çek - class="product-title variant-pdp"
                product_title_elem = page.query_selector('.product-title.variant-pdp')
                if product_title_elem:
                    actual_product_name = product_title_elem.text_content().strip()
                    logger.info(f"   📦 Ürün: {actual_product_name}")
                    product_name = actual_product_name
                
                # "Ürünün Diğer Satıcıları" bölümünü bul
                # Sayfayı scroll et
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(2)
                
                # Satıcı kartlarını bul - "Ürünün Diğer Satıcıları" başlığından sonra
                # Her satıcı bir div içinde, satıcı adı bir link içinde
                
                # Sayfadaki metni al
                page_text = page.evaluate('() => document.body.innerText')
                
                # "Ürünün Diğer Satıcıları" bölümünü ara
                if "Ürünün Diğer Satıcıları" in page_text:
                    logger.info("   ✓ 'Ürünün Diğer Satıcıları' bölümü bulundu")
                    
                    # Satıcı kartlarını bul
                    # Her satıcı bir div içinde, satıcı adı bir link veya span içinde
                    seller_cards = page.query_selector_all('div[class*="seller-card"], div[class*="merchant-card"], div[class*="product-seller"]')
                    
                    logger.info(f"   📊 {len(seller_cards)} satıcı kartı bulundu")
                    
                    for card in seller_cards:
                        try:
                            seller = self._extract_seller_from_card(card, page)
                            if seller and seller.get('name') and seller.get('price', 0) > 0:
                                sellers.append(seller)
                                logger.info(f"   ✓ {seller['name']} - {seller['price']} TL")
                        except Exception as e:
                            logger.warning(f"⚠️ Satıcı kartı çıkarma hatası: {e}")
                            continue
                
                # Eğer satıcı bulunamadıysa, sayfadaki tüm fiyatları ve satıcı adlarını çıkar
                if not sellers:
                    logger.info("   ℹ️ Satıcı kartları bulunamadı, alternatif yöntem kullanılıyor...")
                    sellers = self._extract_sellers_from_text(page_text, product_name)
                
                browser.close()
                
                logger.info(f"✅ Toplam {len(sellers)} satıcı çekildi")
                return sellers
        except Exception as e:
            logger.error(f"❌ Satıcı çekme hatası: {e}")
            return []
    
    def _extract_seller_from_card(self, card, page) -> Optional[Dict]:
        """Satıcı kartından bilgi çıkar"""
        try:
            seller = {
                'name': '',
                'price': 0.0,
                'old_price': 0.0,
                'coupon': '',
                'basket_discount': '',
                'net_price': 0.0,
                'rating': 0.0
            }
            
            # Satıcı adı - link veya span içinde
            name_elem = card.query_selector('a, span[class*="merchant"], span[class*="seller"]')
            if name_elem:
                seller['name'] = name_elem.text_content().strip()
            
            # Rating - yeşil badge içinde
            rating_elem = card.query_selector('[class*="score"], [class*="rating"], span[class*="badge"]')
            if rating_elem:
                rating_text = rating_elem.text_content().strip()
                try:
                    seller['rating'] = float(rating_text.replace(',', '.'))
                except:
                    pass
            
            # Fiyat - TL içeren metin
            card_text = card.text_content()
            price_matches = re.findall(r'(\d{1,5}[.,]\d{3})\s*TL', card_text)
            
            if price_matches:
                # İlk fiyat (genelde indirimli fiyat)
                price_str = price_matches[0].replace('.', '').replace(',', '.')
                seller['price'] = float(price_str)
                seller['net_price'] = seller['price']
                
                # Eğer iki fiyat varsa, ikincisi eski fiyat
                if len(price_matches) > 1:
                    old_price_str = price_matches[1].replace('.', '').replace(',', '.')
                    seller['old_price'] = float(old_price_str)
            
            # Kupon ve indirim bilgisi
            if "İndirimli Kupon" in card_text or "Kupon" in card_text:
                coupon_match = re.search(r'%(\d+)', card_text)
                if coupon_match:
                    seller['coupon'] = f"%{coupon_match.group(1)} Kupon"
            
            if "Sepette" in card_text and "%" in card_text:
                basket_match = re.search(r'Sepette\s*%(\d+)', card_text)
                if basket_match:
                    seller['basket_discount'] = f"Sepette %{basket_match.group(1)} İndirim"
                    # Net fiyatı hesapla
                    basket_percent = int(basket_match.group(1))
                    if seller['price'] > 0:
                        seller['net_price'] = seller['price'] * (1 - basket_percent / 100)
            
            if seller['name'] and seller['price'] > 0:
                return seller
            
            return None
        except Exception as e:
            logger.warning(f"⚠️ Satıcı kartı çıkarma hatası: {e}")
            return None
    
    def _extract_sellers_from_text(self, page_text: str, product_name: str) -> List[Dict]:
        """Sayfadaki metinden satıcıları çıkar (alternatif yöntem)"""
        sellers = []
        try:
            lines = page_text.split('\n')
            
            # Satıcı adlarını ve fiyatlarını ara
            seller_pattern = r'([A-Z][a-zÇçĞğİıÖöŞşÜü]{2,})\s*(\d[.,]\d)\s*(\d{1,5}[.,]\d{3})\s*TL'
            
            matches = re.finditer(seller_pattern, page_text)
            
            for match in matches:
                try:
                    seller = {
                        'name': match.group(1),
                        'rating': float(match.group(2).replace(',', '.')),
                        'price': float(match.group(3).replace('.', '').replace(',', '.')),
                        'old_price': 0.0,
                        'coupon': '',
                        'basket_discount': '',
                        'net_price': 0.0
                    }
                    
                    seller['net_price'] = seller['price']
                    
                    if seller['name'] and seller['price'] > 0:
                        sellers.append(seller)
                except:
                    continue
            
            return sellers
        except Exception as e:
            logger.warning(f"⚠️ Metin çıkarma hatası: {e}")
            return []
    
    def close(self) -> None:
        """Scraper'ı kapat"""
        logger.info("✅ Scraper kapatıldı")

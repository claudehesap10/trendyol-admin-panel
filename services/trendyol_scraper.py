"""
Trendyol Scraper Servisi - Playwright ile JavaScript Desteği
Ürün sayfasındaki tüm satıcıları çeker (fiyat, kupon, indirim, rating)
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
        """Bir ürün için TÜM satıcıları çek"""
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
                
                # Ana satıcıyı çek (sayfanın sağ tarafında)
                main_seller = self._extract_main_seller(page)
                if main_seller:
                    sellers.append(main_seller)
                    logger.info(f"   ✓ Ana Satıcı: {main_seller['name']} - {main_seller['price']} TL")
                
                # Diğer satıcıları çek - "Diğer Satıcılar" bölümünden
                other_sellers = self._extract_other_sellers(page)
                sellers.extend(other_sellers)
                for seller in other_sellers:
                    logger.info(f"   ✓ {seller['name']} - {seller['price']} TL")
                
                browser.close()
                
                logger.info(f"✅ Toplam {len(sellers)} satıcı çekildi")
                return sellers
        except Exception as e:
            logger.error(f"❌ Satıcı çekme hatası: {e}")
            return []
    
    def _extract_main_seller(self, page) -> Optional[Dict]:
        """Ana satıcıyı çek (sayfanın sağ tarafında)"""
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
            
            # Satıcı adı - class="merchant-name"
            merchant_elem = page.query_selector('.merchant-name')
            if merchant_elem:
                seller['name'] = merchant_elem.text_content().strip()
            
            # Rating - class="score-badge"
            rating_elem = page.query_selector('.score-badge')
            if rating_elem:
                rating_text = rating_elem.text_content().strip()
                try:
                    seller['rating'] = float(rating_text.replace(',', '.'))
                except:
                    pass
            
            # Fiyat - class="discounted" veya class="new-price"
            price_elem = page.query_selector('.discounted')
            if not price_elem:
                price_elem = page.query_selector('.new-price')
            
            if price_elem:
                price_text = price_elem.text_content().strip()
                price_match = re.search(r'(\d+[.,]\d+)', price_text)
                if price_match:
                    price_str = price_match.group(1).replace('.', '').replace(',', '.')
                    seller['price'] = float(price_str)
                    seller['net_price'] = seller['price']
            
            # Eski fiyat - class="old-price"
            old_price_elem = page.query_selector('.old-price')
            if old_price_elem:
                old_price_text = old_price_elem.text_content().strip()
                price_match = re.search(r'(\d+[.,]\d+)', old_price_text)
                if price_match:
                    price_str = price_match.group(1).replace('.', '').replace(',', '.')
                    seller['old_price'] = float(price_str)
            
            # Kupon - data-testid="coupon-text"
            coupon_elem = page.query_selector('[data-testid="coupon-text"]')
            if coupon_elem:
                coupon_text = coupon_elem.text_content().strip()
                seller['coupon'] = coupon_text
                
                # Net fiyatı hesapla
                coupon_match = re.search(r'%(\d+)', coupon_text)
                if coupon_match:
                    coupon_percent = int(coupon_match.group(1))
                    if seller['price'] > 0:
                        seller['net_price'] = seller['price'] * (1 - coupon_percent / 100)
            
            # Sepette indirim
            basket_elem = page.query_selector('[class*="basket"]')
            if basket_elem:
                basket_text = basket_elem.text_content().strip()
                if basket_text:
                    seller['basket_discount'] = basket_text
            
            if seller['name'] and seller['price'] > 0:
                return seller
            
            return None
        except Exception as e:
            logger.warning(f"⚠️ Ana satıcı çıkarma hatası: {e}")
            return None
    
    def _extract_other_sellers(self, page) -> List[Dict]:
        """Diğer satıcıları çek - 'Ürünün Diğer Satıcıları' bölümünden"""
        sellers = []
        try:
            # Sayfadaki metni al
            page_text = page.evaluate('() => document.body.innerText')
            
            # "Ürünün Diğer Satıcıları" bölümünü ara
            if "Ürünün Diğer Satıcıları" not in page_text:
                logger.info("   ℹ️ 'Ürünün Diğer Satıcıları' bölümü bulunamadı")
                return sellers
            
            logger.info("   ✓ 'Ürünün Diğer Satıcıları' bölümü bulundu")
            
            # Satıcı kartlarını bul - data-testid veya class'ta "other-merchant" içeren
            seller_items = page.query_selector_all('[data-testid*="other-merchant"], div[class*="other-merchant"]')
            
            if not seller_items:
                # Alternatif: h3 başlığından sonraki div'leri ara
                seller_items = page.query_selector_all('div[id*="other-merchants"] > div')
            
            if not seller_items:
                # Başka bir alternatif
                seller_items = page.query_selector_all('section[data-testid*="other"] > div')
            
            logger.info(f"   📊 {len(seller_items)} satıcı kartı bulundu")
            
            for item in seller_items:
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
                    
                    # Satıcı adı - h3 veya link içinde
                    name_elem = item.query_selector('h3, a[class*="merchant"], span[class*="merchant-name"]')
                    if name_elem:
                        seller['name'] = name_elem.text_content().strip()
                    
                    # Fiyat - TL içeren metin
                    item_text = item.text_content()
                    
                    # Fiyatları ara (iki fiyat olabilir: eski ve yeni)
                    price_matches = re.findall(r'(\d{1,5}[.,]\d{3})\s*TL', item_text)
                    
                    if price_matches:
                        # İlk fiyat (genelde indirimli)
                        price_str = price_matches[0].replace('.', '').replace(',', '.')
                        seller['price'] = float(price_str)
                        seller['net_price'] = seller['price']
                        
                        # Eğer iki fiyat varsa, ikincisi eski fiyat
                        if len(price_matches) > 1:
                            old_price_str = price_matches[1].replace('.', '').replace(',', '.')
                            seller['old_price'] = float(old_price_str)
                    
                    # Rating - yeşil badge içinde
                    rating_elem = item.query_selector('[class*="score"], [class*="rating"], span[class*="badge"]')
                    if rating_elem:
                        rating_text = rating_elem.text_content().strip()
                        try:
                            seller['rating'] = float(rating_text.replace(',', '.'))
                        except:
                            pass
                    
                    # Kupon
                    if "İndirimli Kupon" in item_text or "Kupon" in item_text:
                        coupon_match = re.search(r'%(\d+)', item_text)
                        if coupon_match:
                            seller['coupon'] = f"%{coupon_match.group(1)} Kupon"
                    
                    # Sepette indirim
                    if "Sepette" in item_text and "%" in item_text:
                        basket_match = re.search(r'Sepette\s*%(\d+)', item_text)
                        if basket_match:
                            seller['basket_discount'] = f"Sepette %{basket_match.group(1)} İndirim"
                            # Net fiyatı hesapla
                            basket_percent = int(basket_match.group(1))
                            if seller['price'] > 0:
                                seller['net_price'] = seller['price'] * (1 - basket_percent / 100)
                    
                    if seller['name'] and seller['price'] > 0:
                        sellers.append(seller)
                        logger.info(f"   ✓ {seller['name']} - {seller['price']} TL")
                except Exception as e:
                    logger.warning(f"⚠️ Satıcı kartı çıkarma hatası: {e}")
                    continue
            
            return sellers
        except Exception as e:
            logger.warning(f"⚠️ Diğer satıcılar çıkarma hatası: {e}")
            return []
    
    def close(self) -> None:
        """Scraper'ı kapat"""
        logger.info("✅ Scraper kapatıldı")

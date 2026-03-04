"""
Trendyol Scraper Servisi - Playwright ile JavaScript Desteği
"Ürüne Git" butonlarına tıklayıp her satıcının sayfasından bilgi çeker
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
        """Mağaza sayfasından ürünleri çek - Infinite scroll ile tüm ürünleri yükle"""
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
                
                # Infinite scroll ile tüm ürünleri yükle
                logger.info("📜 Sayfayı scroll edip tüm ürünleri yüklüyorum...")
                last_height = page.evaluate('document.body.scrollHeight')
                scroll_count = 0
                max_scrolls = 50
                
                while scroll_count < max_scrolls:
                    # Sayfayı aşağı scroll et
                    page.evaluate('window.scrollBy(0, window.innerHeight)')
                    time.sleep(1)
                    
                    # Yeni yüksekliği kontrol et
                    new_height = page.evaluate('document.body.scrollHeight')
                    if new_height == last_height:
                        logger.info(f"✅ Tüm ürünler yüklendi ({scroll_count} scroll)")
                        break
                    
                    last_height = new_height
                    scroll_count += 1
                    
                    # Her 5 scroll'da bilgi ver
                    if scroll_count % 5 == 0:
                        logger.info(f"  📜 Scroll {scroll_count}/{max_scrolls}...")
                
                # Ürün linklerini bul
                product_elements = page.query_selector_all('a[href*="?boutiqueId="]')
                
                logger.info(f"📦 {len(product_elements)} ürün linki bulundu")
                
                products = []
                seen_ids = set()
                
                for idx, elem in enumerate(product_elements):
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
                                    if idx % 10 == 0:
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
        """Bir ürün için tüm satıcıları çek - "Ürüne Git" butonlarına tıklayarak"""
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
                time.sleep(2)
                
                # Ürün adını çek
                try:
                    product_title = page.query_selector('h1.product-title')
                    if product_title:
                        actual_product_name = product_title.text_content().strip()
                    else:
                        actual_product_name = product_name
                except:
                    actual_product_name = product_name
                
                sellers = []
                
                # Ana satıcıyı çek
                main_seller = self._extract_main_seller(page)
                if main_seller:
                    main_seller['product_name'] = actual_product_name
                    main_seller['product_url'] = product_url
                    sellers.append(main_seller)
                
                # Diğer satıcıları çek
                other_sellers = self._extract_other_sellers(page)
                for seller in other_sellers:
                    seller['product_name'] = actual_product_name
                    seller['product_url'] = product_url
                    sellers.append(seller)
                
                browser.close()
                
                logger.info(f"✅ Toplam {len(sellers)} satıcı çekildi")
                return sellers
        except Exception as e:
            logger.error(f"❌ Satıcı çekme hatası: {e}")
            return []
    
    def _extract_main_seller(self, page) -> Optional[Dict]:
        """Sayfanın sağ tarafındaki ana satıcıyı çek"""
        try:
            # Satıcı adını çek
            merchant_name_elem = page.query_selector('[class*="merchant-name"]')
            if not merchant_name_elem:
                return None
            
            merchant_name = merchant_name_elem.text_content().strip()
            
            # Rating'i çek
            rating_elem = page.query_selector('[class*="score-badge"]')
            rating = rating_elem.text_content().strip() if rating_elem else "N/A"
            
            # Fiyatı çek
            price_elem = page.query_selector('[class*="discounted"]')
            if not price_elem:
                price_elem = page.query_selector('[class*="new-price"]')
            
            price_text = price_elem.text_content().strip() if price_elem else "N/A"
            price = self._extract_price(price_text)
            
            # Eski fiyatı çek
            old_price_elem = page.query_selector('[class*="old-price"]')
            old_price_text = old_price_elem.text_content().strip() if old_price_elem else ""
            old_price = self._extract_price(old_price_text) if old_price_text else None
            
            # Kupon bilgisini çek
            coupon_elem = page.query_selector('[class*="coupon-text"]')
            coupon_text = coupon_elem.text_content().strip() if coupon_elem else ""
            coupon_discount = self._extract_coupon_discount(coupon_text)
            
            # Sepette indirim bilgisini çek
            basket_discount_elem = page.query_selector('p:has-text("Sepette")')
            basket_discount_text = basket_discount_elem.text_content().strip() if basket_discount_elem else ""
            basket_discount = self._extract_basket_discount(basket_discount_text)
            
            # Son fiyatı hesapla
            final_price = self._calculate_final_price(price, coupon_discount, basket_discount)
            
            logger.info(f"✓ Ana Satıcı: {merchant_name} - {price} TL")
            
            return {
                'merchant_name': merchant_name,
                'rating': rating,
                'original_price': price,
                'old_price': old_price,
                'coupon_discount': coupon_discount,
                'basket_discount': basket_discount,
                'final_price': final_price,
                'notes': self._generate_notes(coupon_discount, basket_discount)
            }
        except Exception as e:
            logger.warning(f"⚠️ Ana satıcı çekme hatası: {e}")
            return None
    
    def _extract_other_sellers(self, page) -> List[Dict]:
        """Diğer satıcıları çek"""
        sellers = []
        try:
            # Diğer satıcılar bölümünü bul
            other_sellers_section = page.query_selector('[class*="other-merchants"]')
            if not other_sellers_section:
                logger.info("ℹ️ 'Diğer Satıcılar' bölümü bulunamadı")
                return sellers
            
            # Satıcı kartlarını bul
            seller_cards = other_sellers_section.query_selector_all('[class*="merchant"]')
            
            logger.info(f"📊 {len(seller_cards)} satıcı kartı bulundu")
            
            for idx, card in enumerate(seller_cards):
                try:
                    # Satıcı adını çek
                    merchant_elem = card.query_selector('[class*="merchant-name"]')
                    if not merchant_elem:
                        continue
                    
                    merchant_name = merchant_elem.text_content().strip()
                    
                    # Rating'i çek
                    rating_elem = card.query_selector('[class*="score-badge"]')
                    rating = rating_elem.text_content().strip() if rating_elem else "N/A"
                    
                    # Fiyatı çek
                    price_elem = card.query_selector('[class*="price"]')
                    price_text = price_elem.text_content().strip() if price_elem else "N/A"
                    price = self._extract_price(price_text)
                    
                    # Eski fiyatı çek
                    old_price_elem = card.query_selector('[class*="old-price"]')
                    old_price_text = old_price_elem.text_content().strip() if old_price_elem else ""
                    old_price = self._extract_price(old_price_text) if old_price_text else None
                    
                    # Kupon bilgisini çek
                    coupon_elem = card.query_selector('[class*="coupon"]')
                    coupon_text = coupon_elem.text_content().strip() if coupon_elem else ""
                    coupon_discount = self._extract_coupon_discount(coupon_text)
                    
                    # Sepette indirim bilgisini çek
                    basket_discount_elem = card.query_selector('p:has-text("Sepette")')
                    basket_discount_text = basket_discount_elem.text_content().strip() if basket_discount_elem else ""
                    basket_discount = self._extract_basket_discount(basket_discount_text)
                    
                    # Son fiyatı hesapla
                    final_price = self._calculate_final_price(price, coupon_discount, basket_discount)
                    
                    sellers.append({
                        'merchant_name': merchant_name,
                        'rating': rating,
                        'original_price': price,
                        'old_price': old_price,
                        'coupon_discount': coupon_discount,
                        'basket_discount': basket_discount,
                        'final_price': final_price,
                        'notes': self._generate_notes(coupon_discount, basket_discount)
                    })
                    
                    logger.info(f"  ✓ Satıcı {idx+1}: {merchant_name} - {price} TL")
                except Exception as e:
                    logger.warning(f"⚠️ Satıcı kartı çekme hatası: {e}")
                    continue
            
            return sellers
        except Exception as e:
            logger.warning(f"⚠️ Diğer satıcılar çekme hatası: {e}")
            return sellers
    
    def _extract_price(self, price_text: str) -> Optional[float]:
        """Fiyat metninden sayıyı çıkar"""
        try:
            # "1.450 TL" formatından sayıyı çıkar
            match = re.search(r'[\d.]+', price_text.replace('.', '').replace(',', '.'))
            if match:
                return float(match.group())
        except:
            pass
        return None
    
    def _extract_coupon_discount(self, coupon_text: str) -> Optional[float]:
        """Kupon indirimini çıkar"""
        try:
            # "%5 İndirimli Kupon!" formatından yüzdeyi çıkar
            match = re.search(r'%(\d+)', coupon_text)
            if match:
                return float(match.group(1))
        except:
            pass
        return None
    
    def _extract_basket_discount(self, basket_text: str) -> Optional[float]:
        """Sepette indirimini çıkar"""
        try:
            # "Sepette %10 İndirim" formatından yüzdeyi çıkar
            match = re.search(r'%(\d+)', basket_text)
            if match:
                return float(match.group(1))
        except:
            pass
        return None
    
    def _calculate_final_price(self, price: Optional[float], coupon: Optional[float], basket: Optional[float]) -> Optional[float]:
        """Son fiyatı hesapla"""
        if not price:
            return None
        
        final = price
        
        # Kupon indirimini uygula
        if coupon:
            final = final * (1 - coupon / 100)
        
        # Sepette indirimini uygula
        if basket:
            final = final * (1 - basket / 100)
        
        return round(final, 2)
    
    def _generate_notes(self, coupon: Optional[float], basket: Optional[float]) -> str:
        """Not oluştur"""
        notes = []
        if coupon:
            notes.append(f"Kupon: %{coupon}")
        if basket:
            notes.append(f"Sepette: %{basket}")
        return " | ".join(notes) if notes else "-"
    
    def close(self):
        """Scraper'ı kapat"""
        pass

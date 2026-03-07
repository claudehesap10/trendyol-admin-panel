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
        """Mağaza sayfasından ürünleri çek - scroll ile"""
        try:
            from playwright.sync_api import sync_playwright

            all_products = []
            seen_ids = set()

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })

                logger.info(f"🌐 Sayfa yükleniyor: {self.store_url}")
                page.goto(self.store_url, wait_until='domcontentloaded', timeout=60000)
                time.sleep(3)

                consecutive_empty = 0
                max_empty = 3  # 3 kez üst üste yeni ürün gelmezse dur

                while consecutive_empty < max_empty:
                    # Mevcut ürünleri topla
                    product_elements = page.query_selector_all('a[href*="-p-"]')

                    new_count = 0
                    for elem in product_elements:
                        try:
                            href = elem.get_attribute('href')
                            if not href or '-p-' not in href:
                                continue

                            if href.startswith('/'):
                                href = 'https://www.trendyol.com' + href

                            product_id_match = re.search(r'-p-(\d+)', href)
                            if not product_id_match:
                                continue
                            product_id = product_id_match.group(1)

                            if product_id in seen_ids:
                                continue

                            # Ürün adını çek
                            name_elem = elem.query_selector(
                                'span[class*="name"], div[class*="name"], '
                                'span[class*="title"], div[class*="title"], h3'
                            )
                            if name_elem:
                                product_name = name_elem.text_content().strip()
                            else:
                                product_name = elem.text_content().strip().split('\n')[0].strip()[:100]

                            for noise in ['Hızlı Bakış', 'Yetkili Satıcı', 'Başarılı Satıcı', 'Sepete Ekle']:
                                product_name = product_name.replace(noise, '').strip()

                            if product_name and len(product_name) > 3:
                                all_products.append({
                                    'id': product_id,
                                    'name': product_name,
                                    'url': href
                                })
                                seen_ids.add(product_id)
                                new_count += 1

                        except Exception as e:
                            logger.warning(f"⚠️ Ürün parse hatası: {e}")
                            continue

                    if new_count > 0:
                        logger.info(f"  ✅ {new_count} yeni ürün (toplam: {len(all_products)})")
                        consecutive_empty = 0
                    else:
                        consecutive_empty += 1
                        logger.info(f"  ⏳ Yeni ürün yok ({consecutive_empty}/{max_empty})")

                    # Sayfanın sonuna scroll et
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    time.sleep(2)

                    # URL'deki pi değerini kontrol et
                    current_url = page.url
                    pi_match = re.search(r'pi=(\d+)', current_url)
                    current_pi = int(pi_match.group(1)) if pi_match else 1
                    logger.info(f"  📄 Mevcut sayfa: pi={current_pi}, toplam: {len(all_products)}")

                browser.close()

            logger.info(f"✅ Toplam {len(all_products)} ürün çekildi")
            return all_products

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
                time.sleep(3)
                
                sellers = []
                actual_product_name = product_name
                
                # Ürün adını çek
                product_title_elem = page.query_selector('.product-title.variant-pdp')
                if product_title_elem:
                    actual_product_name = product_title_elem.text_content().strip()
                    logger.info(f"   📦 Ürün: {actual_product_name}")
                
                # Ana satıcıyı çek (sayfanın sağ tarafında)
                main_seller = self._extract_main_seller(page)
                if main_seller:
                    sellers.append(main_seller)
                    logger.info(f"   ✓ Ana Satıcı: {main_seller['name']} - {main_seller['price']} TL")
                
                # "Diğer Satıcılar" butonunu bul ve tıkla
                other_seller_button = page.query_selector('[data-testid="other-seller-button"], button:has-text("Diğer Satıcılar")')
                if other_seller_button:
                    logger.info("   ℹ️ 'Diğer Satıcılar' butonuna tıklanıyor...")
                    other_seller_button.click()
                    time.sleep(2)
                    
                    # "Ürüne Git" butonlarını bul
                    go_to_product_buttons = page.query_selector_all('button:has-text("Ürüne Git"), a:has-text("Ürüne Git")')
                    logger.info(f"   📊 {len(go_to_product_buttons)} 'Ürüne Git' butonu bulundu")
                    
                    # Her satıcı için "Ürüne Git" butonuna tıkla
                    for i, button in enumerate(go_to_product_buttons[:10]):  # İlk 10 satıcı
                        try:
                            # Butonun URL'sini al
                            seller_url = None
                            
                            if button.get_attribute('href'):
                                seller_url = button.get_attribute('href')
                            else:
                                # Butonun parent'ında link olabilir
                                parent_link = button.query_selector('a')
                                if parent_link:
                                    seller_url = parent_link.get_attribute('href')
                            
                            if not seller_url:
                                # Sayfayı açmadan satıcı bilgisini çek
                                seller = self._extract_seller_from_card(button.evaluate_handle('el => el.closest("div[class*=\"merchant\"], div[class*=\"seller\"]")'))
                                if seller and seller.get('name'):
                                    sellers.append(seller)
                                    logger.info(f"   ✓ {seller['name']} - {seller['price']} TL")
                                continue
                            
                            # URL'yi tam hale getir
                            if seller_url.startswith('/'):
                                seller_url = 'https://www.trendyol.com' + seller_url
                            elif not seller_url.startswith('http'):
                                seller_url = 'https://www.trendyol.com/' + seller_url
                            
                            logger.info(f"   → Satıcı {i+1} sayfasına gidiliyor: {seller_url[:50]}...")
                            
                            # Yeni tab'da satıcı sayfasını aç
                            seller_page = browser.new_page()
                            seller_page.set_extra_http_headers({
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                            })
                            seller_page.goto(seller_url, wait_until='domcontentloaded', timeout=60000)
                            time.sleep(2)
                            
                            # Satıcı bilgisini çek
                            seller = self._extract_seller_from_page(seller_page)
                            if seller and seller.get('name'):
                                sellers.append(seller)
                                logger.info(f"   ✓ {seller['name']} - {seller['price']} TL")
                            
                            seller_page.close()
                        except Exception as e:
                            logger.warning(f"⚠️ Satıcı {i+1} çıkarma hatası: {e}")
                            continue
                else:
                    logger.info("   ℹ️ 'Diğer Satıcılar' butonu bulunamadı")
                
                browser.close()
                
                logger.info(f"✅ Toplam {len(sellers)} satıcı çekildi")
                
                # Ürün adını her satıcıya ekle
                for seller in sellers:
                    seller['product_name'] = actual_product_name
                
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
    
    def _extract_seller_from_page(self, page) -> Optional[Dict]:
        """Satıcı sayfasından bilgi çek"""
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
            
            # Satıcı adı
            merchant_elem = page.query_selector('.merchant-name')
            if merchant_elem:
                seller['name'] = merchant_elem.text_content().strip()
            
            # Rating
            rating_elem = page.query_selector('.score-badge')
            if rating_elem:
                rating_text = rating_elem.text_content().strip()
                try:
                    seller['rating'] = float(rating_text.replace(',', '.'))
                except:
                    pass
            
            # Fiyat
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
            
            # Eski fiyat
            old_price_elem = page.query_selector('.old-price')
            if old_price_elem:
                old_price_text = old_price_elem.text_content().strip()
                price_match = re.search(r'(\d+[.,]\d+)', old_price_text)
                if price_match:
                    price_str = price_match.group(1).replace('.', '').replace(',', '.')
                    seller['old_price'] = float(price_str)
            
            # Kupon
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
            logger.warning(f"⚠️ Satıcı sayfası çıkarma hatası: {e}")
            return None
    
    def _extract_seller_from_card(self, card_handle) -> Optional[Dict]:
        """Satıcı kartından bilgi çek"""
        try:
            # Handle'ı page'e dönüştür
            card = card_handle
            
            seller = {
                'name': '',
                'price': 0.0,
                'old_price': 0.0,
                'coupon': '',
                'basket_discount': '',
                'net_price': 0.0,
                'rating': 0.0
            }
            
            # Satıcı adı
            name_elem = card.query_selector('h3, a[class*="merchant"], span[class*="merchant-name"]')
            if name_elem:
                seller['name'] = name_elem.text_content().strip()
            
            # Fiyat
            card_text = card.text_content()
            price_matches = re.findall(r'(\d{1,5}[.,]\d{3})\s*TL', card_text)
            
            if price_matches:
                price_str = price_matches[0].replace('.', '').replace(',', '.')
                seller['price'] = float(price_str)
                seller['net_price'] = seller['price']
                
                if len(price_matches) > 1:
                    old_price_str = price_matches[1].replace('.', '').replace(',', '.')
                    seller['old_price'] = float(old_price_str)
            
            # Rating
            rating_elem = card.query_selector('[class*="score"], [class*="rating"]')
            if rating_elem:
                rating_text = rating_elem.text_content().strip()
                try:
                    seller['rating'] = float(rating_text.replace(',', '.'))
                except:
                    pass
            
            if seller['name'] and seller['price'] > 0:
                return seller
            
            return None
        except Exception as e:
            logger.warning(f"⚠️ Satıcı kartı çıkarma hatası: {e}")
            return None
    
    def close(self) -> None:
        """Scraper'ı kapat"""
        logger.info("✅ Scraper kapatıldı")

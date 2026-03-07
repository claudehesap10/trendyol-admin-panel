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
        self.merchant_id = self._extract_merchant_id(store_url)
    
    def _extract_merchant_id(self, url: str) -> Optional[str]:
        """URL'den merchant ID'yi çıkar"""
        match = re.search(r'mid=(\d+)', url)
        if match:
            return match.group(1)
        return None
    
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
    
    def fetch_products_via_browser(self) -> List[Dict]:
        """Playwright ile browser kullanarak tüm ürünleri çek (API yerine sayfa üzerinden)"""
        if not self.merchant_id:
            logger.error("❌ Merchant ID bulunamadı!")
            return self.fetch_products()
        
        try:
            logger.info(f"🔍 Browser ile tüm ürünler çekiliyor (Merchant ID: {self.merchant_id})")
            
            from playwright.sync_api import sync_playwright
            
            all_products = []
            page_index = 1
            
            with sync_playwright() as p:
                # GitHub Actions için headless=True kullan
                import os
                is_ci = os.getenv('CI', 'false').lower() == 'true'
                browser = p.chromium.launch(
                    headless=is_ci,  # CI'da headless, local'de görsel
                    args=['--disable-blink-features=AutomationControlled']  # Bot tespitini engelle
                )
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080},
                    locale='tr-TR',
                    timezone_id='Europe/Istanbul'
                )
                
                page = context.new_page()
                
                # İlk sayfayı aç
                logger.info("📄 İlk sayfa açılıyor...")
                page.goto(self.store_url, wait_until='networkidle', timeout=60000)
                time.sleep(3)
                
                # Toplam ürün sayısını bul
                total_products = 0
                try:
                    # Sayfadaki toplam ürün sayısını bulmaya çalış
                    total_text = page.text_content('body')
                    if total_text:
                        # "255 Ürün" gibi bir metin ara
                        import re
                        match = re.search(r'(\d+)\s*Ürün', total_text, re.IGNORECASE)
                        if match:
                            total_products = int(match.group(1))
                            logger.info(f"📦 Toplam {total_products} ürün bulundu")
                except:
                    logger.info("📦 Toplam ürün sayısı tespit edilemedi, tüm sayfalar taranacak")
                
                while True:
                    logger.info(f"📄 Sayfa {page_index} işleniyor...")
                    
                    # Sayfayı tamamen yükle - AGRESIF SCROLL
                    logger.info("  📜 Sayfayı tamamen yüklemek için agresif scroll...")
                    last_height = page.evaluate('document.body.scrollHeight')
                    scroll_attempts = 0
                    max_scroll_attempts = 50  # Daha fazla deneme
                    no_change_count = 0
                    
                    while scroll_attempts < max_scroll_attempts:
                        # Scroll down
                        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                        time.sleep(1.5)  # Daha uzun bekleme
                        
                        # Yeni yüksekliği kontrol et
                        new_height = page.evaluate('document.body.scrollHeight')
                        
                        if new_height == last_height:
                            no_change_count += 1
                            if no_change_count >= 5:  # 5 kez değişiklik yoksa dur
                                logger.info(f"  ✓ Scroll tamamlandı ({scroll_attempts} deneme)")
                                break
                        else:
                            no_change_count = 0
                        
                        last_height = new_height
                        scroll_attempts += 1
                        
                        # Her 5 scroll'da bir durum bildirimi
                        if scroll_attempts % 5 == 0:
                            current_cards = page.query_selector_all('.p-card-wrppr, .p-card-chldrn-cntnr')
                            logger.info(f"  📦 {scroll_attempts} scroll - {len(current_cards)} kart yüklendi")
                    
                    page.evaluate('window.scrollTo(0, 0)')
                    time.sleep(1)
                    
                    # Ürünleri çek
                    product_cards = page.query_selector_all('.p-card-wrppr, .p-card-chldrn-cntnr, [class*="product-card"], a[href*="/p-"]')
                    
                    logger.info(f"  📦 {len(product_cards)} ürün kartı bulundu")
                    
                    if not product_cards:
                        logger.info("✅ Daha fazla ürün bulunamadı")
                        break
                    
                    # Ürünleri işle
                    page_products = []
                    for idx, card in enumerate(product_cards):
                        try:
                            # Debug: İlk birkaç kartın HTML'ini logla
                            if idx < 3:
                                logger.debug(f"  Kart {idx + 1} HTML: {card.inner_html()[:200]}...")
                            
                            # Ürün linkini bul - daha fazla yöntem dene
                            link_elem = None
                            product_url = None
                            
                            # Yöntem 1: Kart kendisi bir link mi?
                            if card.get_attribute('href'):
                                link_elem = card
                                product_url = card.get_attribute('href')
                            
                            # Yöntem 2: İçinde link var mı?
                            if not product_url:
                                link_elem = card.query_selector('a[href*="/p-"]')
                                if link_elem:
                                    product_url = link_elem.get_attribute('href')
                            
                            # Yöntem 3: Herhangi bir a tag'i
                            if not product_url:
                                link_elem = card.query_selector('a')
                                if link_elem:
                                    href = link_elem.get_attribute('href')
                                    if href and '/p-' in href:
                                        product_url = href
                            
                            if not product_url:
                                if idx < 5:
                                    logger.warning(f"  ⚠️ Kart {idx + 1}: URL bulunamadı")
                                continue
                            
                            # Debug log
                            if idx < 3:
                                logger.info(f"  🔗 Kart {idx + 1} URL: {product_url}")
                            
                            # Ürün ID pattern kontrolü - daha esnek
                            # URL formatı: /marka/urun-adi-p-123456?...
                            if not re.search(r'-p-\d+', product_url):
                                if idx < 5:
                                    logger.warning(f"  ⚠️ Kart {idx + 1}: Ürün ID pattern bulunamadı: {product_url[:80]}")
                                continue
                            
                            # URL'yi tam hale getir
                            if product_url.startswith('/'):
                                product_url = 'https://www.trendyol.com' + product_url
                            
                            # Ürün ID'sini çıkar - pattern: /urun-adi-p-123456
                            product_id_match = re.search(r'-p-(\d+)', product_url)
                            if not product_id_match:
                                if idx < 3:
                                    logger.warning(f"  ⚠️ Kart {idx + 1}: ID çıkarılamadı: {product_url[:80]}")
                                continue
                            
                            product_id = product_id_match.group(1)
                            
                            # Zaten eklenmişse atla
                            if any(p['id'] == product_id for p in all_products):
                                continue
                            
                            # Ürün adını bul
                            product_name = ''
                            name_elem = card.query_selector('.prdct-desc-cntnr-name, .name, [class*="product-name"], [class*="prdct-desc"]')
                            if name_elem:
                                product_name = name_elem.text_content().strip()
                            
                            if not product_name:
                                # Link text'inden al
                                link_elem = card.query_selector('a')
                                if link_elem:
                                    product_name = link_elem.get_attribute('title') or link_elem.text_content().strip()
                            
                            # Temizle
                            product_name = product_name.replace('Hızlı Bakış', '').replace('Yetkili Satıcı', '').strip()
                            
                            if not product_name or len(product_name) < 3:
                                if idx < 3:
                                    logger.warning(f"  ⚠️ Kart {idx + 1}: Ürün adı bulunamadı")
                                continue
                            
                            # Fiyat bilgisi
                            price = 0.0
                            price_elem = card.query_selector('.prc-box-dscntd, .prc-box-sllng, [class*="price"]')
                            if price_elem:
                                price_text = price_elem.text_content().strip()
                                price_match = re.search(r'(\d+(?:[.,]\d+)?)', price_text.replace('.', ''))
                                if price_match:
                                    price = float(price_match.group(1).replace(',', '.'))
                            
                            # Marka
                            brand = ''
                            brand_elem = card.query_selector('.prdct-desc-cntnr-ttl, [class*="brand"]')
                            if brand_elem:
                                brand = brand_elem.text_content().strip()
                            
                            # Görsel
                            image = ''
                            img_elem = card.query_selector('img')
                            if img_elem:
                                image = img_elem.get_attribute('src') or ''
                            
                            product_data = {
                                'id': product_id,
                                'name': product_name,
                                'url': product_url,
                                'price': price,
                                'brand': brand,
                                'image': image
                            }
                            
                            all_products.append(product_data)
                            page_products.append(product_data)
                            
                        except Exception as e:
                            logger.warning(f"⚠️ Ürün kartı işleme hatası: {e}")
                            continue
                    
                    logger.info(f"  ✓ {len(page_products)} yeni ürün eklendi (Toplam: {len(all_products)})")
                    
                    # Scroll yöntemi kullanıldığında tek sayfa yeterli
                    logger.info(f"✅ Scroll ile tüm ürünler yüklendi - pagination gerekmiyor")
                    break

                    
                    # Sonraki sayfa var mı kontrol et - Birden fazla selector dene
                    next_button = None
                    next_selectors = [
                        'a.fltr-item-next',
                        'button.fltr-item-next', 
                        'a[title="Sonraki Sayfa"]',
                        'a[aria-label="Sonraki Sayfa"]',
                        '.paginationContent a:last-child:not(.disabled)',
                        'a.ty-pagination-next',
                        'button.ty-pagination-next',
                        'a:has-text("›")',
                        'button:has-text("›")',
                    ]
                    
                    for selector in next_selectors:
                        try:
                            next_button = page.query_selector(selector)
                            if next_button:
                                # Disabled mi kontrol et
                                classes = next_button.get_attribute('class') or ''
                                aria_disabled = next_button.get_attribute('aria-disabled') or ''
                                
                                if 'disabled' not in classes.lower() and aria_disabled != 'true':
                                    logger.info(f"  ✓ Sonraki sayfa butonu bulundu: {selector}")
                                    break
                                else:
                                    next_button = None
                        except:
                            continue
                    
                    if not next_button:
                        # Manuel pagination: URL ile sayfa geçişi
                        logger.info(f"  🔍 Buton yok, manuel pagination deneniyor...")
                        next_page = page_index + 1
                        next_url = f"https://www.trendyol.com/sr?mid={self.merchant_id}&os=1&pi={next_page}"
                        
                        try:
                            logger.info(f"  🔗 Sayfa {next_page}'e gidiliyor: {next_url}")
                            page.goto(next_url, wait_until='domcontentloaded', timeout=30000)
                            page.wait_for_timeout(3000)
                            
                            # Ürün kartı var mı kontrol et
                            test_cards = page.query_selector_all('.p-card-wrppr, .p-card-chldrn-cntnr')
                            if len(test_cards) > 0:
                                logger.info(f"  ✅ Sayfa {next_page} yüklendi ({len(test_cards)} kart)")
                                page_index = next_page
                                continue  # Döngüye devam et
                            else:
                                logger.info(f"✅ Sayfa {next_page}'de ürün yok - son sayfaya ulaşıldı")
                                break
                        except Exception as e:
                            logger.info(f"✅ Sayfa {next_page} yüklenemedi - son sayfaya ulaşıldı: {str(e)[:100]}")
                            break
                    
                    # Sonraki sayfaya git
                    logger.info(f"  → Sayfa {page_index + 1}'e geçiliyor...")
                    try:
                        # Butona scroll et
                        next_button.scroll_into_view_if_needed()
                        time.sleep(0.5)
                        
                        # Tıkla
                        next_button.click()
                        
                        # Sayfanın yüklenmesini bekle
                        time.sleep(3)
                        page.wait_for_load_state('domcontentloaded', timeout=30000)
                        time.sleep(2)
                        
                        page_index += 1
                        logger.info(f"  ✓ Sayfa {page_index}'e geçildi")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Sonraki sayfaya geçiş hatası: {e}")
                        logger.info("  🔄 URL ile geçiş deneniyor...")
                        
                        # Alternatif: URL ile geçiş
                        try:
                            current_url = page.url
                            if 'pi=' in current_url:
                                # Mevcut page index'i artır
                                import re
                                new_url = re.sub(r'pi=\d+', f'pi={page_index + 1}', current_url)
                            else:
                                # pi parametresi yoksa ekle
                                separator = '&' if '?' in current_url else '?'
                                new_url = f"{current_url}{separator}pi={page_index + 1}"
                            
                            logger.info(f"  → Yeni URL: {new_url}")
                            page.goto(new_url, wait_until='networkidle', timeout=30000)
                            time.sleep(2)
                            page_index += 1
                            logger.info(f"  ✓ URL ile sayfa {page_index}'e geçildi")
                            
                        except Exception as e2:
                            logger.error(f"  ❌ URL ile geçiş de başarısız: {e2}")
                            break
                
                browser.close()
                
            logger.info(f"✅ Browser ile {len(all_products)} ürün çekildi")
            return all_products
            
        except Exception as e:
            logger.error(f"❌ Browser ile ürün çekme hatası: {e}")
            logger.info("🔄 Eski yönteme geri dönülüyor...")
            return self.fetch_products()
    
    def fetch_products_via_api(self) -> List[Dict]:
        """Trendyol API'sini kullanarak tüm ürünleri çek"""
        logger.warning("⚠️ API yöntemi bot koruması nedeniyle çalışmıyor")
        logger.info("🔄 Browser yöntemine geçiliyor...")
        return self.fetch_products_via_browser()
    
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
                
                # Infinite scroll ile tüm ürünleri yükle
                logger.info("📜 Sayfayı scroll edip tüm ürünleri yüklüyorum...")
                last_height = page.evaluate('document.body.scrollHeight')
                scroll_count = 0
                max_scrolls = 50
                
                while scroll_count < max_scrolls:
                    page.evaluate('window.scrollBy(0, window.innerHeight)')
                    time.sleep(0.5)
                    new_height = page.evaluate('document.body.scrollHeight')
                    if new_height == last_height:
                        logger.info(f"✅ Tüm ürünler yüklendi ({scroll_count} scroll)")
                        break
                    last_height = new_height
                    scroll_count += 1
                    if scroll_count % 10 == 0:
                        logger.info(f"  📜 Scroll {scroll_count}...")
                
                # Ürün linklerini bul
                product_elements = page.query_selector_all('a[href*="?boutiqueId="]')
                
                logger.info(f"📦 {len(product_elements)} ürün linki bulundu")
                
                products = []
                seen_ids = set()
                
                for elem in product_elements:
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

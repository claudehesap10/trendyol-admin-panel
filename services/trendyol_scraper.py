'''
Trendyol Scraper Servisi - Playwright ile JavaScript Desteği
"Ürüne Git" butonlarına tıklayıp her satıcının sayfasından bilgi çeker
'''
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

    def _extract_seller_id_from_url(self, url: str) -> Optional[str]:
        """URL'den satıcı ID'sini çıkarır."""
        if not url:
            return None
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
    
    def fetch_products_via_api(self) -> List[Dict]:
        """Trendyol API'si üzerinden tüm ürünleri çek"""
        try:
            logger.info("🔍 API ile tüm ürünler çekiliyor...")
            
            from playwright.sync_api import sync_playwright
            
            all_products = []
            page_index = 1
            
            with sync_playwright() as p:
                # GitHub Actions için headless=True kullan
                import os
                is_ci = os.getenv("CI", "false").lower() == "true"
                browser = p.chromium.launch(
                    headless=is_ci,  # CI'da headless, local'de görsel
                    args=["--disable-blink-features=AutomationControlled"]  # Bot tespitini engelle
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="tr-TR",
                    timezone_id="Europe/Istanbul"
                )
                
                page = context.new_page()
                
                # İlk sayfayı aç
                logger.info("📄 İlk sayfa açılıyor...")
                page.goto(self.store_url, wait_until="networkidle", timeout=60000)
                time.sleep(3)
                
                # Toplam ürün sayısını bul
                total_products = 0
                try:
                    # Sayfadaki toplam ürün sayısını bulmaya çalış
                    total_text = page.text_content("body")
                    if total_text:
                        # "255 Ürün" gibi bir metin ara
                        import re
                        match = re.search(r"(\d+)\s*Ürün", total_text, re.IGNORECASE)
                        if match:
                            total_products = int(match.group(1))
                            logger.info(f"📦 Toplam {total_products} ürün bulundu")
                except:
                    logger.info("📦 Toplam ürün sayısı tespit edilemedi, tüm sayfalar taranacak")
                
                while True:
                    logger.info(f"📄 Sayfa {page_index} işleniyor...")
                    
                    # Sayfayı tamamen yükle - AGRESIF SCROLL
                    logger.info("  📜 Sayfayı tamamen yüklemek için agresif scroll...")
                    last_height = page.evaluate("document.body.scrollHeight")
                    scroll_attempts = 0
                    max_scroll_attempts = 50  # Daha fazla deneme
                    no_change_count = 0
                    
                    while scroll_attempts < max_scroll_attempts:
                        # Scroll down
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        time.sleep(1.5)  # Daha uzun bekleme
                        
                        # Yeni yüksekliği kontrol et
                        new_height = page.evaluate("document.body.scrollHeight")
                        
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
                            current_cards = page.query_selector_all(".p-card-wrppr, .p-card-chldrn-cntnr")
                            logger.info(f"  📦 {scroll_attempts} scroll - {len(current_cards)} kart yüklendi")
                    
                    page.evaluate("window.scrollTo(0, 0)")
                    time.sleep(1)
                    
                    # Ürünleri çek
                    product_cards = page.query_selector_all(".p-card-wrppr, .p-card-chldrn-cntnr, [class*=\"product-card\"], a[href*=\"/p-\"]")
                    
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
                            if card.get_attribute("href"):
                                link_elem = card
                                product_url = card.get_attribute("href")
                            
                            # Yöntem 2: İçinde link var mı?
                            if not product_url:
                                link_elem = card.query_selector("a[href*=\"/p-\"]")
                                if link_elem:
                                    product_url = link_elem.get_attribute("href")
                            
                            # Yöntem 3: Herhangi bir a tag'i
                            if not product_url:
                                link_elem = card.query_selector("a")
                                if link_elem:
                                    href = link_elem.get_attribute("href")
                                    if href and "/p-" in href:
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
                            if not re.search(r"-p-\d+", product_url):
                                if idx < 5:
                                    logger.warning(f"  ⚠️ Kart {idx + 1}: Ürün ID pattern bulunamadı: {product_url[:80]}")
                                continue
                            
                            # URL'yi tam hale getir
                            if product_url.startswith("/"):
                                product_url = "https://www.trendyol.com" + product_url
                            
                            # Ürün ID'sini çıkar - pattern: /urun-adi-p-123456
                            product_id_match = re.search(r"-p-(\d+)", product_url)
                            if not product_id_match:
                                if idx < 3:
                                    logger.warning(f"  ⚠️ Kart {idx + 1}: ID çıkarılamadı: {product_url[:80]}")
                                continue
                            
                            product_id = product_id_match.group(1)
                            
                            # Zaten eklenmişse atla
                            if any(p["id"] == product_id for p in all_products):
                                continue
                            
                            # Ürün adını bul
                            product_name = ""
                            name_elem = card.query_selector(".prdct-desc-cntnr-name, .name, [class*=\"product-name\"], [class*=\"prdct-desc\"]")
                            if name_elem:
                                product_name = name_elem.text_content().strip()
                            
                            if not product_name:
                                # Link text'inden al
                                link_elem = card.query_selector("a")
                                if link_elem:
                                    product_name = link_elem.get_attribute("title") or link_elem.text_content().strip()
                            
                            # Fiyatı bul
                            price_elem = card.query_selector(".prc-box-sllng, .prc-slg, .price-box .price")
                            price = 0.0
                            if price_elem:
                                price_text = price_elem.text_content().strip()
                                price_match = re.search(r"(\d+[.,]\d+)", price_text)
                                if price_match:
                                    price_str = price_match.group(1).replace(".", "").replace(",", ".")
                                    price = float(price_str)
                            
                            if product_name and price > 0:
                                all_products.append({
                                    "id": product_id,
                                    "name": product_name,
                                    "url": product_url,
                                    "price": price # Kendi fiyatımızı da çekiyoruz
                                })
                                logger.info(f"  ✅ Ürün eklendi: {product_name} - {price} TL")
                            else:
                                if idx < 5:
                                    logger.warning(f"  ⚠️ Kart {idx + 1}: Ürün adı veya fiyatı bulunamadı")
                            
                        except Exception as e:
                            logger.warning(f"⚠️ Ürün kartı işleme hatası: {e}")
                            continue
                    
                    # Sonraki sayfaya geç
                    page_index += 1
                    next_page_button = page.query_selector(f"a[href*=\"pi={page_index}\"]")
                    if next_page_button:
                        logger.info(f"➡️ Sonraki sayfaya gidiliyor: Sayfa {page_index}")
                        next_page_button.click()
                        page.wait_for_load_state("networkidle")
                        time.sleep(2)
                    else:
                        logger.info("✅ Tüm sayfalar tarandı.")
                        break
                
                browser.close()
                return all_products
        except Exception as e:
            logger.error(f"❌ API ile ürün çekme hatası: {e}")
            return []

    def fetch_sellers_for_product(self, product_url: str, product_name: str) -> List[Dict]:
        """Belirli bir ürün için tüm satıcıları çek"""
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(product_url, wait_until='networkidle')

                sellers = []

                # Ana satıcıyı (Buy Box sahibi) al
                main_seller = self._extract_main_seller(page)
                if main_seller:
                    sellers.append(main_seller)

                # Diğer satıcıları al
                other_sellers_button = page.query_selector('button:has-text("Diğer Satıcılar")')
                if other_sellers_button:
                    other_sellers_button.click()
                    page.wait_for_selector('.other-sellers-container', timeout=5000)
                    
                    seller_cards = page.query_selector_all('.other-seller-item') # Bu selector'ı sayfa yapısına göre güncellemek gerekebilir
                    for card in seller_cards:
                        seller = self._extract_seller_from_card(card)
                        if seller:
                            sellers.append(seller)

                browser.close()

                # Her satıcıya ürün bilgilerini ekle
                for seller in sellers:
                    seller['product_name'] = product_name
                    seller['product_url'] = product_url

                return sellers
        except Exception as e:
            logger.error(f"❌ Satıcıları çekerken hata: {e}")
            return []

    def _extract_main_seller(self, page) -> Optional[Dict]:
        """Sayfadaki ana satıcıyı (Buy Box) çıkarır."""
        try:
            seller_name_element = page.query_selector('.merchant-box-wrapper .merchant-name')
            price_element = page.query_selector('.product-price-container .prc-dsc')
            seller_link_element = page.query_selector('.merchant-box-wrapper a')

            if seller_name_element and price_element:
                price_text = price_element.inner_text().strip().split(' ')[0].replace('.', '').replace(',', '.')
                seller_url = seller_link_element.get_attribute('href') if seller_link_element else ''
                full_seller_url = f"https://www.trendyol.com{seller_url}" if seller_url.startswith('/') else seller_url

                return {
                    'name': seller_name_element.inner_text().strip(),
                    'price': float(price_text),
                    'id': self._extract_seller_id_from_url(full_seller_url),
                    'rating': 0.0 # Gerekirse bu da scrape edilebilir
                }
        except Exception as e:
            logger.warning(f"⚠️ Ana satıcı çıkarılırken hata: {e}")
        return None

    def _extract_seller_from_card(self, card) -> Optional[Dict]:
        """Diğer satıcılar listesindeki bir karttan satıcı bilgilerini çıkarır."""
        try:
            seller_name_element = card.query_selector('.seller-name-text')
            price_element = card.query_selector('.prc-slg')
            seller_link_element = card.query_selector('a') # Genellikle kartın kendisi link olur

            if seller_name_element and price_element:
                price_text = price_element.inner_text().strip().split(' ')[0].replace('.', '').replace(',', '.')
                seller_url = seller_link_element.get_attribute('href') if seller_link_element else ''
                full_seller_url = f"https://www.trendyol.com{seller_url}" if seller_url.startswith('/') else seller_url

                return {
                    'name': seller_name_element.inner_text().strip(),
                    'price': float(price_text),
                    'id': self._extract_seller_id_from_url(full_seller_url),
                    'rating': 0.0 # Gerekirse bu da scrape edilebilir
                }
        except Exception as e:
            logger.warning(f"⚠️ Satıcı kartından bilgi çıkarılırken hata: {e}")
        return None

    def close(self) -> None:
        """Scraper'ı kapat"""
        logger.info("✅ Scraper kapatıldı")

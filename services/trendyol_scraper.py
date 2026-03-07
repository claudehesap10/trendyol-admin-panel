"""
Trendyol Scraper Servisi - API tabanlı, tüm ürünleri çeker
"""
import logging
import re
import time
import requests
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class TrendyolScraper:
    """Trendyol mağazasından veri çeker"""
    
    def __init__(self, store_url: str, max_retries: int = 3, retry_delay: int = 5):
        self.store_url = store_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.merchant_id = self._extract_merchant_id(store_url)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': 'https://www.trendyol.com/',
        }
    
    def _extract_merchant_id(self, url: str) -> Optional[str]:
        """URL'den merchantId çıkar"""
        # Format 1: ?mid=1126746
        match = re.search(r'mid=(\d+)', url)
        if match:
            return match.group(1)
        # Format 2: /magaza/isim-m-1126746
        match = re.search(r'-m-(\d+)', url)
        if match:
            return match.group(1)
        logger.error(f"❌ merchantId bulunamadı: {url}")
        return None

    def initialize(self) -> bool:
        """Scraper'ı başlat"""
        if not self.merchant_id:
            logger.error("❌ Geçerli bir merchant ID bulunamadı")
            return False
        logger.info(f"✅ Scraper başlatıldı - Merchant ID: {self.merchant_id}")
        return True

    def fetch_products(self) -> List[Dict]:
        """Trendyol API'sini sayfalayarak tüm ürünleri çek"""
        if not self.merchant_id:
            logger.error("❌ merchantId yok, ürünler çekilemiyor")
            return []

        all_products = []
        page = 1
        page_size = 24

        logger.info(f"🔍 Ürünler çekiliyor - Merchant: {self.merchant_id}")

        while True:
            url = (
                f"https://apigw.trendyol.com/discovery-sfint-search-service/api/search/products/"
                f"?mid={self.merchant_id}&os=1&pi={page}&pathModel=sr"
                f"&channelId=1&culture=tr-TR&pageSize={page_size}"
            )

            success = False
            for attempt in range(self.max_retries):
                try:
                    response = requests.get(url, headers=self.headers, timeout=30)
                    response.raise_for_status()
                    data = response.json()

                    products = data.get("products", [])
                    if not products:
                        logger.info(f"✅ Tüm ürünler çekildi. Toplam: {len(all_products)}")
                        return all_products

                    for p in products:
                        product_url = p.get('url', '')
                        if product_url.startswith('/'):
                            product_url = 'https://www.trendyol.com' + product_url

                        price_data = p.get('price', {})
                        all_products.append({
                            'id': str(p.get('id', '')),
                            'name': p.get('name', ''),
                            'url': product_url,
                            'brand': p.get('brand', ''),
                            'category': p.get('category', {}).get('name', ''),
                            'price': price_data.get('current', 0),
                            'old_price': price_data.get('old', 0),
                            'image': p.get('image', ''),
                            'merchant_id': p.get('merchantId', ''),
                        })

                    logger.info(f"📦 Sayfa {page}: {len(products)} ürün (toplam: {len(all_products)})")

                    # Sonraki sayfa yoksa dur
                    if not data.get("_links", {}).get("next"):
                        logger.info(f"✅ Son sayfaya ulaşıldı. Toplam: {len(all_products)}")
                        return all_products

                    success = True
                    break

                except requests.exceptions.RequestException as e:
                    logger.warning(f"⚠️ Sayfa {page}, deneme {attempt+1}/{self.max_retries}: {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)

            if not success:
                logger.error(f"❌ Sayfa {page} {self.max_retries} denemede çekilemedi, duruyorum")
                break

            page += 1
            time.sleep(0.5)

        return all_products

    def fetch_sellers_for_product(self, product_url: str, product_name: str = "") -> List[Dict]:
        """Bir ürün için tüm satıcıları çek - Playwright ile"""
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

                # Ana satıcıyı çek
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

                    go_to_product_buttons = page.query_selector_all('button:has-text("Ürüne Git"), a:has-text("Ürüne Git")')
                    logger.info(f"   📊 {len(go_to_product_buttons)} 'Ürüne Git' butonu bulundu")

                    for i, button in enumerate(go_to_product_buttons[:10]):
                        try:
                            seller_url = button.get_attribute('href')

                            if not seller_url:
                                parent_link = button.query_selector('a')
                                if parent_link:
                                    seller_url = parent_link.get_attribute('href')

                            if not seller_url:
                                seller = self._extract_seller_from_card(
                                    button.evaluate_handle('el => el.closest("div[class*=\'merchant\'], div[class*=\'seller\']")')
                                )
                                if seller and seller.get('name'):
                                    sellers.append(seller)
                                    logger.info(f"   ✓ {seller['name']} - {seller['price']} TL")
                                continue

                            if seller_url.startswith('/'):
                                seller_url = 'https://www.trendyol.com' + seller_url
                            elif not seller_url.startswith('http'):
                                seller_url = 'https://www.trendyol.com/' + seller_url

                            logger.info(f"   → Satıcı {i+1}: {seller_url[:60]}...")

                            seller_page = browser.new_page()
                            seller_page.set_extra_http_headers({
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                            })
                            seller_page.goto(seller_url, wait_until='domcontentloaded', timeout=60000)
                            time.sleep(2)

                            seller = self._extract_seller_from_page(seller_page)
                            if seller and seller.get('name'):
                                sellers.append(seller)
                                logger.info(f"   ✓ {seller['name']} - {seller['price']} TL")

                            seller_page.close()

                        except Exception as e:
                            logger.warning(f"⚠️ Satıcı {i+1} hatası: {e}")
                            continue
                else:
                    logger.info("   ℹ️ 'Diğer Satıcılar' butonu bulunamadı")

                browser.close()

                for seller in sellers:
                    seller['product_name'] = actual_product_name

                logger.info(f"✅ Toplam {len(sellers)} satıcı çekildi")
                return sellers

        except Exception as e:
            logger.error(f"❌ Satıcı çekme hatası: {e}")
            return []

    def _extract_main_seller(self, page) -> Optional[Dict]:
        """Ana satıcıyı çek"""
        try:
            seller = {
                'name': '', 'price': 0.0, 'old_price': 0.0,
                'coupon': '', 'basket_discount': '', 'net_price': 0.0, 'rating': 0.0
            }

            merchant_elem = page.query_selector('.merchant-name')
            if merchant_elem:
                seller['name'] = merchant_elem.text_content().strip()

            rating_elem = page.query_selector('.score-badge')
            if rating_elem:
                try:
                    seller['rating'] = float(rating_elem.text_content().strip().replace(',', '.'))
                except:
                    pass

            price_elem = page.query_selector('.discounted') or page.query_selector('.new-price')
            if price_elem:
                price_match = re.search(r'(\d+[.,]\d+)', price_elem.text_content().strip())
                if price_match:
                    seller['price'] = float(price_match.group(1).replace('.', '').replace(',', '.'))
                    seller['net_price'] = seller['price']

            old_price_elem = page.query_selector('.old-price')
            if old_price_elem:
                price_match = re.search(r'(\d+[.,]\d+)', old_price_elem.text_content().strip())
                if price_match:
                    seller['old_price'] = float(price_match.group(1).replace('.', '').replace(',', '.'))

            coupon_elem = page.query_selector('[data-testid="coupon-text"]')
            if coupon_elem:
                coupon_text = coupon_elem.text_content().strip()
                seller['coupon'] = coupon_text
                coupon_match = re.search(r'%(\d+)', coupon_text)
                if coupon_match and seller['price'] > 0:
                    seller['net_price'] = seller['price'] * (1 - int(coupon_match.group(1)) / 100)

            basket_elem = page.query_selector('[class*="basket"]')
            if basket_elem:
                seller['basket_discount'] = basket_elem.text_content().strip()

            return seller if seller['name'] and seller['price'] > 0 else None

        except Exception as e:
            logger.warning(f"⚠️ Ana satıcı hatası: {e}")
            return None

    def _extract_seller_from_page(self, page) -> Optional[Dict]:
        """Satıcı sayfasından bilgi çek"""
        return self._extract_main_seller(page)

    def _extract_seller_from_card(self, card_handle) -> Optional[Dict]:
        """Satıcı kartından bilgi çek"""
        try:
            seller = {
                'name': '', 'price': 0.0, 'old_price': 0.0,
                'coupon': '', 'basket_discount': '', 'net_price': 0.0, 'rating': 0.0
            }

            name_elem = card_handle.query_selector('h3, a[class*="merchant"], span[class*="merchant-name"]')
            if name_elem:
                seller['name'] = name_elem.text_content().strip()

            card_text = card_handle.text_content()
            price_matches = re.findall(r'(\d{1,5}[.,]\d{3})\s*TL', card_text)
            if price_matches:
                seller['price'] = float(price_matches[0].replace('.', '').replace(',', '.'))
                seller['net_price'] = seller['price']
                if len(price_matches) > 1:
                    seller['old_price'] = float(price_matches[1].replace('.', '').replace(',', '.'))

            rating_elem = card_handle.query_selector('[class*="score"], [class*="rating"]')
            if rating_elem:
                try:
                    seller['rating'] = float(rating_elem.text_content().strip().replace(',', '.'))
                except:
                    pass

            return seller if seller['name'] and seller['price'] > 0 else None

        except Exception as e:
            logger.warning(f"⚠️ Kart hatası: {e}")
            return None

    def close(self) -> None:
        logger.info("✅ Scraper kapatıldı")

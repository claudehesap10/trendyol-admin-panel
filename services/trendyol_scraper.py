"""
Trendyol Scraper Servisi - Playwright intercept yaklaşımı
"""
import logging
import re
import time
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class TrendyolScraper:
    """Trendyol mağazasından veri çeker"""
    
    def __init__(self, store_url: str, max_retries: int = 3, retry_delay: int = 5):
        self.store_url = store_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.merchant_id = self._extract_merchant_id(store_url)

    def _extract_merchant_id(self, url: str) -> Optional[str]:
        """URL'den merchantId çıkar"""
        match = re.search(r'mid=(\d+)', url)
        if match:
            return match.group(1)
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

    def _parse_product(self, p: dict) -> dict:
        """Ham API verisini temiz dict'e çevir"""
        product_url = p.get('url', '')
        if product_url.startswith('/'):
            product_url = 'https://www.trendyol.com' + product_url
        price_data = p.get('price', {})
        return {
            'id': str(p.get('id', '')),
            'name': p.get('name', ''),
            'url': product_url,
            'brand': p.get('brand', ''),
            'category': p.get('category', {}).get('name', ''),
            'price': price_data.get('current', 0),
            'old_price': price_data.get('old', 0),
            'image': p.get('image', ''),
            'merchant_id': p.get('merchantId', ''),
        }

    def fetch_products(self) -> List[Dict]:
        """Playwright ile API response'larını intercept ederek tüm ürünleri çek"""
        if not self.merchant_id:
            logger.error("❌ merchantId yok")
            return []

        from playwright.sync_api import sync_playwright

        all_products = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()

            api_responses = []

            def handle_response(response):
                if 'search/products' in response.url and response.status == 200:
                    try:
                        data = response.json()
                        if data.get('products'):
                            api_responses.append({'url': response.url, 'data': data})
                            logger.info(f"🎯 API yakalandı: {len(data['products'])} ürün")
                    except:
                        pass

            page.on("response", handle_response)

            # İlk sayfayı yükle
            logger.info("🌐 İlk sayfa yükleniyor...")
            page.goto(self.store_url, wait_until='networkidle', timeout=60000)
            time.sleep(3)

            if not api_responses:
                logger.error("❌ Hiç API response yakalanamadı")
                browser.close()
                return []

            first_data = api_responses[0]['data']
            total = first_data.get('total', 0)
            logger.info(f"📦 Toplam ürün sayısı: {total}")

            for p_data in first_data.get('products', []):
                all_products.append(self._parse_product(p_data))

            logger.info(f"📦 Sayfa 1: {len(all_products)}/{total}")

            # Kalan sayfaları gez
            page_num = 2
            while len(all_products) < total:
                api_responses.clear()

                next_url = (
                    f"{self.store_url}&pi={page_num}"
                    if '?' in self.store_url
                    else f"{self.store_url}?pi={page_num}"
                )

                logger.info(f"📄 Sayfa {page_num} yükleniyor...")

                success = False
                for attempt in range(self.max_retries):
                    try:
                        page.goto(next_url, wait_until='networkidle', timeout=60000)
                        time.sleep(2)

                        if api_responses:
                            success = True
                            break
                        else:
                            logger.warning(f"⚠️ Sayfa {page_num}, deneme {attempt+1}/{self.max_retries}: Response yakalanamadı")
                            time.sleep(self.retry_delay)
                    except Exception as e:
                        logger.warning(f"⚠️ Sayfa {page_num}, deneme {attempt+1}/{self.max_retries}: {e}")
                        time.sleep(self.retry_delay)

                if not success:
                    logger.error(f"❌ Sayfa {page_num} {self.max_retries} denemede çekilemedi, duruyorum")
                    break

                page_data = api_responses[0]['data']
                products = page_data.get('products', [])

                if not products:
                    logger.info("✅ Ürün kalmadı, tamamlandı")
                    break

                for p_data in products:
                    all_products.append(self._parse_product(p_data))

                logger.info(f"📦 Sayfa {page_num}: {len(products)} ürün (toplam: {len(all_products)}/{total})")

                if not page_data.get('_links', {}).get('next'):
                    logger.info("✅ Son sayfaya ulaşıldı")
                    break

                page_num += 1
                time.sleep(1)

            browser.close()

        logger.info(f"✅ Toplam {len(all_products)} ürün çekildi")
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

                # Diğer Satıcılar butonunu bul
                other_seller_button = page.query_selector(
                    '[data-testid="other-seller-button"], button:has-text("Diğer Satıcılar")'
                )
                if other_seller_button:
                    logger.info("   ℹ️ 'Diğer Satıcılar' butonuna tıklanıyor...")
                    other_seller_button.click()
                    time.sleep(2)

                    go_to_product_buttons = page.query_selector_all(
                        'button:has-text("Ürüne Git"), a:has-text("Ürüne Git")'
                    )
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
                                    button.evaluate_handle(
                                        'el => el.closest("div[class*=\'merchant\'], div[class*=\'seller\']")'
                                    )
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

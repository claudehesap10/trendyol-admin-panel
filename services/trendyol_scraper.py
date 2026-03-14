"""
Trendyol Scraper Servisi - Playwright ile JavaScript Desteği

Trendyol'da fiyat katmanları:
  1. Liste Fiyatı (old_price)   → üstü çizili, örn: 1.680 TL
  2. Satış Fiyatı (price)       → asıl etiket fiyatı, örn: 1.680 TL
  3. Kupon İndirimi (coupon)    → pembe badge, örn: "50 TL Kupon Fırsatı!" veya "%2 Kupon"
  4. Sepette İndirimi (basket)  → yeşil banner, örn: "Sepette %5 İndirim"
  5. Son Fiyat (net_price)      → tüm indirimler uygulandıktan sonra gerçek fiyat

Excele yazılan alanlar:
  - Orijinal Fiyat (TL)  = liste/satış fiyatı (indirimler öncesi)
  - Kupon İndirimi       = kupon metni (varsa)
  - Sepette İndirimi     = sepet indirim metni (varsa)
  - Son Fiyat (TL)       = net_price (tüm indirimler sonrası)
"""

import logging
import re
import time
import os
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class TrendyolScraper:

    def __init__(self, store_url: str, max_retries: int = 3, retry_delay: int = 5):
        self.store_url = store_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.merchant_id = self._extract_merchant_id(store_url)

    # ──────────────────────────────────────────────────────────────────────────
    # YARDIMCI METODLAR
    # ──────────────────────────────────────────────────────────────────────────

    def _extract_merchant_id(self, url: str) -> Optional[str]:
        match = re.search(r'mid=(\d+)|merchantId=(\d+)', url)
        return (match.group(1) or match.group(2)) if match else None

    def _clean_product_url(self, url: str) -> str:
        """
        merchantId ve query string'i kaldır → tarafsız ürün sayfası.
        merchantId ile açılınca Trendyol o satıcıya yönlendiriyor,
        satıcı Buy Box'ta değilse Esvento kayboluyor.
        """
        clean = re.sub(r'\?.*$', '', url.strip())
        if clean.startswith('/'):
            clean = 'https://www.trendyol.com' + clean
        return clean

    def _parse_price(self, text: str) -> float:
        """
        Trendyol fiyat metinlerini float'a çevir.
        
        Türkçe format: binlik ayraç=nokta, ondalık=virgül
          "1.499 TL"    → 1499.0   (sadece nokta, binlik ayraç)
          "1.234,56 TL" → 1234.56  (nokta binlik, virgül ondalık)
          "1234,56"     → 1234.56  (sadece virgül, ondalık)
          "1.596"       → 1596.0   (sadece nokta, binlik ayraç)
        
        Kritik kural: Eğer sadece nokta varsa VE noktadan sonra tam 3 rakam varsa
        → binlik ayraç, nokta kaldırılır.
        Eğer sadece nokta varsa VE noktadan sonra 1-2 rakam varsa → ondalık.
        """
        if not text:
            return 0.0
        try:
            cleaned = re.sub(r'[^\d,.]', '', text.strip())
            if not cleaned:
                return 0.0

            if ',' in cleaned and '.' in cleaned:
                # "1.234,56" → binlik nokta + ondalık virgül
                cleaned = cleaned.replace('.', '').replace(',', '.')

            elif ',' in cleaned and '.' not in cleaned:
                # "1234,56" → sadece ondalık virgül
                cleaned = cleaned.replace(',', '.')

            elif '.' in cleaned and ',' not in cleaned:
                # Sadece nokta var — binlik mi ondalık mı?
                parts = cleaned.split('.')
                if len(parts) == 2 and len(parts[1]) == 3:
                    # "1.499" → 1499 (binlik ayraç)
                    cleaned = cleaned.replace('.', '')
                elif len(parts) > 2:
                    # "1.234.567" → tüm noktalar binlik
                    cleaned = cleaned.replace('.', '')
                # else: "1.5" gibi → ondalık, olduğu gibi bırak

            return float(cleaned)
        except:
            return 0.0

    def _compute_net_price(self, price: float, coupon: str, basket_discount: str,
                            basket_net_price: float) -> float:
        """
        Gerçek son fiyatı hesapla.
        
        Öncelik sırası:
        1. Eğer sayfa "Sepette X TL" olarak direkt fiyatı gösteriyorsa → onu kullan
        2. Yoksa: price üzerine kupon + sepet indirimini uygula
        
        Trendyol'da genellikle sepet indirimi sayfada doğrudan hesaplanmış
        "Sepette 1.596 TL" şeklinde gösteriliyor. Bu değeri yakaladıysak en güvenilir.
        """
        if basket_net_price > 0:
            return basket_net_price  # En güvenilir: sayfa direkt hesaplamış

        net = price
        if not net:
            return 0.0

        # Kupon indirimi uygula
        if coupon:
            # "%5 İndirim" veya "50 TL Kupon" formatları
            pct_match = re.search(r'%(\d+)', coupon)
            tl_match = re.search(r'(\d+(?:[.,]\d+)?)\s*TL', coupon)
            if pct_match:
                net = round(net * (1 - int(pct_match.group(1)) / 100), 2)
            elif tl_match:
                tl_val = self._parse_price(tl_match.group(1))
                if tl_val > 0:
                    net = round(net - tl_val, 2)

        # Sepette indirim uygula
        if basket_discount:
            pct_match = re.search(r'%(\d+)', basket_discount)
            tl_match = re.search(r'(\d+(?:[.,]\d+)?)\s*TL', basket_discount)
            if pct_match:
                net = round(net * (1 - int(pct_match.group(1)) / 100), 2)
            elif tl_match:
                tl_val = self._parse_price(tl_match.group(1))
                if tl_val > 0:
                    net = round(net - tl_val, 2)

        return max(net, 0.0)

    def _make_browser_context(self, playwright):
        is_ci = os.getenv('CI', 'false').lower() == 'true'
        browser = playwright.chromium.launch(
            headless=is_ci,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='tr-TR',
            timezone_id='Europe/Istanbul'
        )
        return browser, context

    def initialize(self) -> bool:
        try:
            try:
                from playwright.sync_api import sync_playwright
                logger.info("✅ Playwright bulundu")
            except ImportError:
                import subprocess
                subprocess.check_call(['pip', 'install', 'playwright'])
                subprocess.check_call(['playwright', 'install', 'chromium'])
                logger.info("✅ Playwright yüklendi")
            return True
        except Exception as e:
            logger.error(f"❌ Başlatma hatası: {e}")
            return False

    # ──────────────────────────────────────────────────────────────────────────
    # ÜRÜN LİSTESİ — Tek sayfada agresif infinite scroll
    #
    # Trendyol mağaza sayfası (sr?mid=X) infinite scroll kullanıyor.
    # pi=2, pi=3 gibi pagination parametreleri çalışmıyor — sayfa 1'i tekrar döndürüyor.
    # Tüm ürünleri almak için tek sayfada yeterince scroll yapmak gerekiyor.
    # ──────────────────────────────────────────────────────────────────────────

    def fetch_products_via_browser(self) -> List[Dict]:
        if not self.merchant_id:
            logger.error("❌ Merchant ID yok!")
            return []

        try:
            from playwright.sync_api import sync_playwright
            all_products = []
            seen_ids = set()

            with sync_playwright() as p:
                browser, context = self._make_browser_context(p)
                page = context.new_page()

                url = f"https://www.trendyol.com/sr?mid={self.merchant_id}&os=1"
                logger.info(f"📄 Mağaza sayfası açılıyor: {url}")

                page.goto(url, wait_until='domcontentloaded', timeout=60000)
                time.sleep(3)

                # Toplam ürün sayısını oku (varsa) — hedef kart sayısı için
                total_expected = self._read_total_product_count(page)
                if total_expected:
                    logger.info(f"📦 Hedef: {total_expected} ürün")

                # Agresif infinite scroll
                cards = self._scroll_until_all_loaded(page, total_expected)

                logger.info(f"📦 Scroll sonrası {len(cards)} kart bulundu")

                for card in cards:
                    product = self._extract_product_from_card(card, seen_ids)
                    if product:
                        all_products.append(product)
                        seen_ids.add(product['id'])

                browser.close()

            logger.info(f"✅ {len(all_products)} ürün çekildi")
            return all_products

        except Exception as e:
            logger.error(f"❌ Ürün çekme hatası: {e}")
            return []

    def _read_total_product_count(self, page) -> int:
        """
        Sayfadaki "255+ Ürün" veya "255 Ürün" metninden toplam ürün sayısını oku.
        Bulunamazsa 0 döner.
        """
        try:
            body = page.text_content('body') or ''
            match = re.search(r'(\d+)\+?\s*[Üü]r[üu]n', body)
            if match:
                return int(match.group(1))
        except:
            pass
        return 0

    def _scroll_until_all_loaded(self, page, total_expected: int = 0):
        """
        Tüm ürünler yüklenene kadar scroll yap.

        Strateji:
        1. Sayfayı küçük adımlarla scroll et
        2. Her adımda yeni kart gelip gelmediğini kontrol et
        3. Durma koşulları:
           a. Hedef sayıya ulaştıysak (total_expected > 0)
           b. Çok uzun süre (200 deneme) yeni kart gelmediyse
           c. En fazla 500 scroll denemesi
        """
        last_count = 0
        no_new_cards = 0
        max_no_new = 15      # 15 kez yeni kart gelmeyince dur
        max_attempts = 500   # Mutlak maksimum scroll

        for attempt in range(max_attempts):
            # Küçük adımlarla scroll — lazy load'u tetiklemek için
            page.evaluate('window.scrollBy(0, 600)')
            time.sleep(1.5)

            cards = self._find_product_cards(page)
            current_count = len(cards)

            if current_count > last_count:
                new = current_count - last_count
                logger.info(f"  📜 Scroll {attempt+1}: {current_count} kart (+{new})")
                last_count = current_count
                no_new_cards = 0

                # Hedefe ulaştıysak dur
                if total_expected > 0 and current_count >= total_expected:
                    logger.info(f"  ✅ Hedefe ulaşıldı: {current_count}/{total_expected}")
                    break
            else:
                no_new_cards += 1

                # "Daha Fazla Göster" butonu var mı?
                try:
                    btn = page.query_selector(
                        'button:has-text("Daha Fazla"), button:has-text("Yükle"), '
                        'button:has-text("Göster")'
                    )
                    if btn and btn.is_visible():
                        logger.info(f"  🔘 'Daha Fazla' butonu bulundu, tıklanıyor...")
                        btn.scroll_into_view_if_needed()
                        btn.click()
                        time.sleep(2)
                        no_new_cards = 0  # Butona tıkladıktan sonra sıfırla
                        continue
                except:
                    pass

                if no_new_cards >= max_no_new:
                    logger.info(f"  ✅ {max_no_new} denemede yeni kart yok — scroll tamamlandı ({current_count} kart)")
                    break

        # Başa dön, tüm kartları topla
        page.evaluate('window.scrollTo(0, 0)')
        time.sleep(1)
        return self._find_product_cards(page)

    def _find_product_cards(self, page) -> list:
        """
        Trendyol'un güncel HTML yapısına göre ürün kartlarını bul.
        Debug çıktısına göre doğru selector'lar:
          - [class*="product-card"] → 24 eleman ✅
          - a[href*="boutiqueId"]   → 24 eleman ✅  (URL /p- değil boutiqueId içeriyor)
          - .p-card-wrppr           → 0 eleman  ✗  (eski yapı)
        """
        # Öncelik sırasına göre dene
        for sel in [
            '[class*="product-card"]',
            '[data-testid*="card"]',
            '[data-testid*="product"]',
            '.p-card-wrppr',           # Eski yapı, fallback
            '.p-card-chldrn-cntnr',    # Eski yapı, fallback
        ]:
            try:
                elems = page.query_selector_all(sel)
                if elems:
                    return elems
            except:
                continue
        return []

    def _extract_product_from_card(self, card, seen_ids: set) -> Optional[Dict]:
        try:
            product_url = None

            # Kart kendisi link mi?
            if card.get_attribute('href'):
                product_url = card.get_attribute('href')

            # boutiqueId içeren link (güncel Trendyol URL formatı)
            if not product_url:
                link = card.query_selector('a[href*="boutiqueId"]')
                if link:
                    product_url = link.get_attribute('href')

            # /p- içeren link (eski format, fallback)
            if not product_url:
                link = card.query_selector('a[href*="/p-"]')
                if link:
                    product_url = link.get_attribute('href')

            # Herhangi bir a tag'i
            if not product_url:
                link = card.query_selector('a')
                if link:
                    href = link.get_attribute('href') or ''
                    if 'trendyol.com' in href or href.startswith('/'):
                        product_url = href

            if not product_url:
                return None

            if product_url.startswith('/'):
                product_url = 'https://www.trendyol.com' + product_url

            # Product ID — iki format:
            # Yeni: /urun-adi-p-123456?boutiqueId=...
            # veya URL'de -p-XXXXX pattern'i
            pid_match = re.search(r'-p-(\d+)', product_url)
            if not pid_match:
                # Alternatif: contentId veya productId parametresi
                pid_match = re.search(r'(?:contentId|productId)=(\d+)', product_url)
            if not pid_match:
                return None

            pid = pid_match.group(1)
            if pid in seen_ids:
                return None

            # Ürün adı
            name = ''
            for sel in [
                '[class*="product-name"]', '[class*="ProductName"]',
                '[class*="prdct-desc"]', '.prdct-desc-cntnr-name',
                'h2', 'h3', 'span[class*="name"]'
            ]:
                e = card.query_selector(sel)
                if e:
                    name = e.text_content().strip()
                    if name and len(name) > 3:
                        break

            if not name:
                link = card.query_selector('a')
                if link:
                    name = link.get_attribute('title') or link.text_content().strip()

            name = re.sub(r'Hızlı Bakış|Yetkili Satıcı|Başarılı Satıcı', '', name).strip()
            if not name or len(name) < 3:
                return None

            return {'id': pid, 'name': name, 'url': product_url}
        except Exception as e:
            logger.warning(f"  ⚠️ Kart parse hatası: {e}")
            return None

    def fetch_products_via_api(self) -> List[Dict]:
        return self.fetch_products_via_browser()

    def fetch_products(self) -> List[Dict]:
        return self.fetch_products_via_browser()

    # ──────────────────────────────────────────────────────────────────────────
    # SATICI ÇEKME — Ana metod
    # ──────────────────────────────────────────────────────────────────────────

    def fetch_sellers_for_product(self, product_url: str, product_name: str = "") -> List[Dict]:
        try:
            logger.info(f"🔍 {product_name or product_url[:60]}")
            from playwright.sync_api import sync_playwright

            clean_url = self._clean_product_url(product_url)
            sellers = []
            actual_name = product_name

            with sync_playwright() as p:
                browser, context = self._make_browser_context(p)
                page = context.new_page()

                loaded = False
                for attempt in range(self.max_retries):
                    try:
                        page.goto(clean_url, wait_until='domcontentloaded', timeout=60000)
                        time.sleep(3)
                        loaded = True
                        break
                    except Exception as e:
                        logger.warning(f"  ⚠️ Deneme {attempt+1}: {e}")
                        if attempt < self.max_retries - 1:
                            time.sleep(self.retry_delay)

                if not loaded:
                    browser.close()
                    return []

                # Ürün adı
                for sel in ['.product-title', 'h1.pr-new-br', 'h1[class*="product"]', 'h1']:
                    e = page.query_selector(sel)
                    if e:
                        n = e.text_content().strip()
                        if n and len(n) > 5:
                            actual_name = n
                            break

                # 1. Buy Box satıcısı (ana sayfa)
                buy_box = self._extract_buy_box_seller(page)
                if buy_box:
                    sellers.append(buy_box)
                    logger.info(f"  ✓ Buy Box: {buy_box['name']} — ₺{buy_box['net_price']} (kupon: {buy_box['coupon'] or '-'}, sepet: {buy_box['basket_discount'] or '-'})")

                # 2. "Diğer Satıcılar" paneli
                if self._open_other_sellers_panel(page):
                    others = self._parse_all_sellers_from_panel(page, buy_box)
                    sellers.extend(others)
                    logger.info(f"  ✓ Panelden {len(others)} satıcı eklendi")

                browser.close()

            for s in sellers:
                s['product_name'] = actual_name

            logger.info(f"  ✅ Toplam {len(sellers)} satıcı: {[s['name'] for s in sellers]}")
            return sellers

        except Exception as e:
            logger.error(f"❌ Satıcı çekme hatası: {e}")
            return []

    # ──────────────────────────────────────────────────────────────────────────
    # BUY BOX SATICI ÇEKME
    # ──────────────────────────────────────────────────────────────────────────

    def _extract_buy_box_seller(self, page) -> Optional[Dict]:
        """
        Ana sayfanın sağ panelindeki Buy Box satıcısını çek.
        Tüm fiyat katmanlarını ayrı ayrı çeker.
        """
        s = {
            'name': '', 'price': 0.0, 'old_price': 0.0,
            'coupon': '', 'basket_discount': '', 'net_price': 0.0, 'rating': 0.0
        }

        try:
            # Satıcı adı
            for sel in ['.merchant-name', '[class*="merchant-name"]',
                        '[data-testid="seller-name"]', 'a[class*="merchant"]']:
                e = page.query_selector(sel)
                if e:
                    name = e.text_content().strip()
                    if name:
                        s['name'] = name
                        break
            if not s['name']:
                return None

            # Rating
            for sel in ['.score-badge', '[class*="score-badge"]']:
                e = page.query_selector(sel)
                if e:
                    try:
                        s['rating'] = float(e.text_content().strip().replace(',', '.'))
                    except:
                        pass
                    break

            # Satış fiyatı (kupon/sepet öncesi)
            for sel in ['.prc-dsc', '.discounted', '[class*="prc-dsc"]',
                        '[class*="discounted"]', '.new-price', '.prc-box-dscntd']:
                e = page.query_selector(sel)
                if e:
                    price = self._parse_price(e.text_content())
                    if price > 0:
                        s['price'] = price
                        break

            # Eski/liste fiyatı
            for sel in ['.old-price', '.prc-org', '[class*="old-price"]', '.prc-box-orgnl']:
                e = page.query_selector(sel)
                if e:
                    price = self._parse_price(e.text_content())
                    if price > 0:
                        s['old_price'] = price
                        break

            # Kupon — Trendyol'da iki format:
            # - "50 TL Kupon Fırsatı!" (pembe badge, sayfanın ortasında)
            # - "%2 İndirimli Kupon!" (yüzdelik)
            coupon_selectors = [
                '[data-testid="coupon-text"]',
                '.coupon-text',
                '[class*="coupon-text"]',
                '[class*="coupon"] span',
                # Pembe kupon badge'i
                '.badge-coupon',
                '[class*="badge"][class*="coupon"]',
                # Genel: "Kupon" kelimesi geçen element
                'span:has-text("Kupon")',
                'div:has-text("Kupon Fırsatı")',
            ]
            for sel in coupon_selectors:
                try:
                    e = page.query_selector(sel)
                    if e:
                        text = e.text_content().strip()
                        # "Kupon" veya "%" içermeli, UI çöpü olmasın
                        if text and ('kupon' in text.lower() or '%' in text) and len(text) < 60:
                            s['coupon'] = text
                            break
                except:
                    continue

            # Sepette indirim — Trendyol'da iki yerde gösteriyor:
            # 1. Yeşil banner: "Sepette %5 İndirim" + "Sepette 1.596 TL"
            # 2. Sağ panel / kampanyalar listesi
            basket_net_price = 0.0
            basket_selectors = [
                # Yeşil "Sepette X İndirim" banner
                '[class*="basket-discount"]',
                '[class*="cart-discount"]',
                '[class*="sepette"]',
                # "Sepette Uygulanacak" kampanya
                '[class*="campaign"][class*="basket"]',
                # Genel: "Sepette" kelimesi geçen ve indirim ifadesi olan
                'span:has-text("Sepette %")',
                'div:has-text("Sepette %")',
            ]
            for sel in basket_selectors:
                try:
                    e = page.query_selector(sel)
                    if e:
                        text = e.text_content().strip()
                        if text and 'sepette' in text.lower() and len(text) < 80:
                            s['basket_discount'] = text
                            break
                except:
                    continue

            # "Sepette X TL" şeklinde direkt fiyat gösteriyorsa yakala
            # Örn: "Sepette 1.596 TL" → basket_net_price = 1596.0
            basket_price_selectors = [
                '[class*="basket-price"]',
                '[class*="cart-price"]',
                # Yeşil fiyat elementi
                'span[class*="prc"][class*="basket"]',
                'span[class*="basket"][class*="prc"]',
            ]
            for sel in basket_price_selectors:
                try:
                    e = page.query_selector(sel)
                    if e:
                        price = self._parse_price(e.text_content())
                        if price > 0:
                            basket_net_price = price
                            break
                except:
                    continue

            # Net fiyatı hesapla
            s['net_price'] = self._compute_net_price(
                s['price'], s['coupon'], s['basket_discount'], basket_net_price
            )
            # net_price hesaplanamadıysa satış fiyatını kullan
            if s['net_price'] <= 0:
                s['net_price'] = s['price']

            return s if s['name'] and s['price'] > 0 else None

        except Exception as e:
            logger.warning(f"  ⚠️ Buy Box çıkarma hatası: {e}")
            return None

    # ──────────────────────────────────────────────────────────────────────────
    # DİĞER SATICILAR PANELİ
    # ──────────────────────────────────────────────────────────────────────────

    def _open_other_sellers_panel(self, page) -> bool:
        selectors = [
            '[data-testid="other-seller-button"]',
            'button:has-text("Diğer Satıcılar")',
            'a:has-text("Diğer Satıcılar")',
            '[class*="other-seller"] button',
            'button:has-text("satıcı")',
            '[class*="seller-count"]',
        ]
        for sel in selectors:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.scroll_into_view_if_needed()
                    time.sleep(0.3)
                    btn.click()
                    time.sleep(2)
                    logger.info("  ✓ 'Diğer Satıcılar' paneli açıldı")
                    return True
            except:
                continue
        return False

    def _parse_all_sellers_from_panel(self, page, buy_box: Optional[Dict]) -> List[Dict]:
        buy_box_name = (buy_box.get('name') or '').strip().lower() if buy_box else ''
        elems = self._find_panel_seller_elements(page)

        if not elems:
            logger.warning("  ⚠️ Panel elementi bulunamadı")
            try:
                panel = page.query_selector('[class*="other-seller"], [class*="otherSeller"]')
                if panel:
                    logger.info(f"  🔍 Panel HTML: {panel.inner_html()[:400]}")
            except:
                pass
            return []

        sellers = []
        seen_names = {buy_box_name}  # Buy Box'ı da duplicate set'e ekle

        for elem in elems:
            try:
                seller = self._parse_single_seller_card(elem)
                if not seller or not seller.get('name') or seller['price'] <= 0:
                    continue

                name_lower = seller['name'].strip().lower()

                # "Ürüne Git" butonu satıcı değil — atla
                if name_lower in ('ürüne git', 'urune git', 'sepete ekle', 'satıcıya git'):
                    continue

                # Duplicate kontrolü — aynı isim tekrar gelmesin
                if name_lower in seen_names:
                    continue
                seen_names.add(name_lower)

                sellers.append(seller)
                logger.info(f"  ✓ {seller['name']} — ₺{seller['net_price']} (kupon: {seller['coupon'] or '-'}, sepet: {seller['basket_discount'] or '-'})")
            except Exception as e:
                logger.warning(f"  ⚠️ Kart parse hatası: {e}")

        return sellers

    def _find_panel_seller_elements(self, page) -> list:
        """
        "Diğer Satıcılar" panelindeki satıcı elementlerini bul.
        
        Log'dan görülen gerçek HTML yapısı:
          side-other-seller-total-container
            └── other-seller-item-total-container  ← her satıcı için bir tane
                  └── other-seller-item-other-seller-container
                        └── other-seller-header-header
                              └── other-seller-header-header-area
                                    └── a href="/sr?mid=..."  ← satıcı linki
        """
        # Gerçek Trendyol panel yapısına göre — her satıcı bir "item" container
        selectors = [
            '[data-testid="other-seller-item"]',
            '.other-seller-item-total-container',
            '[class*="other-seller-item"]',
            '[class*="otherSeller"] [class*="item"]',
        ]

        for sel in selectors:
            try:
                elems = page.query_selector_all(sel)
                if elems:
                    logger.info(f"  🔍 '{sel}' → {len(elems)} eleman")
                    return elems
            except:
                continue

        # Fallback: merchantId içeren linklerin parent container'larını bul
        # Her satıcının /sr?mid=X linki var
        try:
            seller_links = page.query_selector_all('a[href*="/sr?mid="]')
            if seller_links:
                # Her linkin en yakın anlamlı container'ını al
                containers = []
                seen_mids = set()
                for link in seller_links:
                    href = link.get_attribute('href') or ''
                    mid_match = re.search(r'mid=(\d+)', href)
                    if not mid_match:
                        continue
                    mid = mid_match.group(1)
                    if mid in seen_mids:
                        continue
                    seen_mids.add(mid)
                    # Linkin satıcı bilgilerini içeren en yakın büyük container
                    container = link.evaluate_handle(
                        'el => el.closest("[class*=\'other-seller-item\'], [class*=\'seller-item\'], [class*=\'merchant-item\']") || el.parentElement?.parentElement?.parentElement'
                    )
                    if container:
                        containers.append(container)
                if containers:
                    logger.info(f"  🔍 mid= link fallback: {len(containers)} benzersiz satıcı")
                    return containers
        except:
            pass

        # Son fallback: fiyat içeren merchant/seller div'leri (duplicate riski var, sonradan filtrele)
        try:
            candidates = page.query_selector_all('div[class*="other-seller"]')
            valid = [d for d in candidates
                     if re.search(r'\d+[.,]\d+', d.text_content() or '')
                     and len((d.text_content() or '').strip()) > 10]
            if valid:
                logger.info(f"  🔍 Fallback div: {len(valid)} eleman")
            return valid[:20]
        except:
            return []

    def _parse_single_seller_card(self, elem) -> Optional[Dict]:
        """
        Panel içindeki tek bir satıcı kartından tüm fiyat katmanlarını çıkar.
        
        Image 1'deki Mass Coffee kartı örneği:
          - İsim: "Mass Coffee"
          - Rating: 9.7
          - "2. Ürüne %2 İndirim" (kampanya etiketi — kupon değil, atla)
          - "Kargo Bedava"
          - "Sepette %5 İndirim" (basket_discount)
          - "Sepette 1.596 TL" (basket_net_price — direkt hesaplanmış)
          - "1.680 TL" (liste/satış fiyatı)
        """
        s = {
            'name': '', 'price': 0.0, 'old_price': 0.0,
            'coupon': '', 'basket_discount': '', 'net_price': 0.0, 'rating': 0.0
        }

        # ── İsim ──────────────────────────────────────────────────────────
        for sel in ['.merchant-name', '[class*="merchant-name"]', '[class*="seller-name"]',
                    'a[class*="merchant"]', 'h3', 'h4', 'span[class*="name"]']:
            e = elem.query_selector(sel)
            if e:
                name = e.text_content().strip()
                if 2 < len(name) < 80:
                    s['name'] = name
                    break

        if not s['name']:
            full = elem.text_content() or ''
            cleaned = re.sub(r'\d+[.,]\d+\s*TL|%\d+|Ürüne Git|Sepete Ekle|Satıcıya Git|'
                             r'Sepette|Kupon|Kargo|İndirim|Hızlı|Teslimat', '', full).strip()
            if 2 < len(cleaned) < 60:
                s['name'] = cleaned

        # ── Satış fiyatı ──────────────────────────────────────────────────
        for sel in ['.prc-dsc', '.discounted', '[class*="prc-dsc"]',
                    '[class*="discounted"]', '.new-price', '[class*="price"]',
                    'span[class*="prc"]']:
            e = elem.query_selector(sel)
            if e:
                price = self._parse_price(e.text_content())
                if price > 0:
                    s['price'] = price
                    break

        if s['price'] <= 0:
            s['price'] = self._parse_price(elem.text_content())

        # ── Eski/liste fiyatı ──────────────────────────────────────────────
        for sel in ['.old-price', '[class*="old-price"]', '[class*="prc-org"]']:
            e = elem.query_selector(sel)
            if e:
                price = self._parse_price(e.text_content())
                if price > 0:
                    s['old_price'] = price
                    break

        # ── Rating ────────────────────────────────────────────────────────
        for sel in ['.score-badge', '[class*="score-badge"]', '[class*="rating"]']:
            e = elem.query_selector(sel)
            if e:
                try:
                    s['rating'] = float(e.text_content().strip().replace(',', '.'))
                    break
                except:
                    pass

        # ── Kupon ─────────────────────────────────────────────────────────
        # Panel kartında: "50 TL Kupon Fırsatı!" veya "%2 İndirimli Kupon"
        # DİKKAT: "2. Ürüne %2 İndirim" kupon DEĞİL, kampanya etiketi — atla
        coupon_selectors = [
            '[data-testid="coupon-text"]',
            '.coupon-text',
            '[class*="coupon-text"]',
            '[class*="coupon"] span',
            'span:has-text("Kupon")',
        ]
        for sel in coupon_selectors:
            try:
                e = elem.query_selector(sel)
                if e:
                    text = e.text_content().strip()
                    if text and 'kupon' in text.lower() and len(text) < 60:
                        s['coupon'] = text
                        break
            except:
                continue

        # ── Sepette indirim ───────────────────────────────────────────────
        # Panel kartında: "Sepette %5 İndirim" yeşil badge
        basket_net_price = 0.0
        basket_selectors = [
            '[class*="basket-discount"]',
            '[class*="cart-discount"]',
            '[class*="sepette"]',
            'span:has-text("Sepette %")',
            'div:has-text("Sepette %")',
        ]
        for sel in basket_selectors:
            try:
                e = elem.query_selector(sel)
                if e:
                    text = e.text_content().strip()
                    if text and 'sepette' in text.lower() and len(text) < 80:
                        s['basket_discount'] = text
                        break
            except:
                continue

        # "Sepette X TL" direkt fiyatı yakala
        # Panel kartında yeşil renkte "Sepette 1.596 TL" gösteriyor
        basket_price_selectors = [
            '[class*="basket-price"]',
            '[class*="cart-price"]',
            'span[class*="prc"][class*="basket"]',
            # Yeşil renk genellikle ayrı bir class ile gösteriliyor
            'span[class*="green"][class*="prc"]',
            'span[class*="prc-grn"]',
        ]
        for sel in basket_price_selectors:
            try:
                e = elem.query_selector(sel)
                if e:
                    price = self._parse_price(e.text_content())
                    if price > 0:
                        basket_net_price = price
                        break
            except:
                continue

        # ── Net fiyat hesapla ─────────────────────────────────────────────
        s['net_price'] = self._compute_net_price(
            s['price'], s['coupon'], s['basket_discount'], basket_net_price
        )
        if s['net_price'] <= 0:
            s['net_price'] = s['price']

        return s if s['name'] and s['price'] > 0 else None

    def close(self) -> None:
        logger.info("✅ Scraper kapatıldı")
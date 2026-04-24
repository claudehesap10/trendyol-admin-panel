"""
Kritik düzeltmeler:
  1. Fiyat sanity check — kendi fiyatımızın %60'ından ucuz rakip fiyatı şüpheli, logla
  2. Satıcı adı doğrulama — çekilen satıcı gerçekten o satıcı mı kontrol et
  3. Net fiyat: kupon 100 TL ise liste - 100 = net olmalı
  4. URL temizleme: boutiqueId + merchantId + tüm query string kaldır
"""

import re
import logging
import time
import os
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Fiyat parse (değişmedi)
# ─────────────────────────────────────────────────────────────────────────────

def parse_price(text: str) -> float:
    if not text:
        return 0.0
    try:
        cleaned = re.sub(r'[^\d,.]', '', str(text).strip())
        if not cleaned:
            return 0.0
        if ',' in cleaned and '.' in cleaned:
            cleaned = cleaned.replace('.', '').replace(',', '.')
        elif ',' in cleaned:
            cleaned = cleaned.replace(',', '.')
        elif '.' in cleaned:
            parts = cleaned.split('.')
            if len(parts) == 2 and len(parts[1]) == 3:
                cleaned = cleaned.replace('.', '')
            elif len(parts) > 2:
                cleaned = cleaned.replace('.', '')
        val = float(cleaned)
        return val if 0 < val < 150000 else 0.0
    except:
        return 0.0


def compute_net_price(price: float, coupon: str, basket_discount: str,
                       basket_net_price: float, coupon_max_tl: float = 0.0) -> float:
    """
    Öncelik:
      1. Sepette X TL direkt gösteriliyorsa → kullan (akıl sağlığı kontrolü ile)
      2. Yoksa: price - kupon - sepet (kupon max TL limitini uygula)

    Akıl sağlığı kontrolü: sepette fiyatı, liste fiyatının %35'inden düşükse
    ve hiç kupon/sepet indirimi yoksa, bu değer büyük ihtimalle başka bir
    üründen (öneri widget'ı vb.) yanlış yakalanmıştır — atla.
    """
    if basket_net_price > 0 and price > 0:
        ratio = basket_net_price / price
        has_discount = bool(coupon or basket_discount)
        if ratio >= 0.35 or has_discount:
            return round(basket_net_price, 2)
        else:
            logger.warning(
                f"  ⚠️ ŞÜPHELİ SEPET FİYATI: basket_net=₺{basket_net_price} "
                f"liste=₺{price} (oran={ratio:.2f}) kupon='{coupon}' — atlanıyor"
            )
    elif basket_net_price > 0:
        return round(basket_net_price, 2)

    net = price
    if not net:
        return 0.0

    if coupon:
        pct = re.search(r'%(\d+)', coupon)
        tl  = re.search(r'(\d[\d.,]*)\s*TL', coupon)
        if pct:
            discount = round(net * int(pct.group(1)) / 100, 2)
            if coupon_max_tl > 0:
                discount = min(discount, coupon_max_tl)
            net = round(net - discount, 2)
        elif tl:
            tl_val = parse_price(tl.group(1))
            if tl_val > 0:
                net = round(net - tl_val, 2)

    if basket_discount:
        pct = re.search(r'%(\d+)', basket_discount)
        tl  = re.search(r'(\d[\d.,]*)\s*TL', basket_discount)
        if pct:
            net = round(net * (1 - int(pct.group(1)) / 100), 2)
        elif tl:
            tl_val = parse_price(tl.group(1))
            if tl_val > 0:
                net = round(net - tl_val, 2)

    return max(net, 0.0)


# ─────────────────────────────────────────────────────────────────────────────
# SCRAPER
# ─────────────────────────────────────────────────────────────────────────────

class TrendyolScraper:

    def __init__(self, store_url: str, max_retries: int = 3, retry_delay: int = 5,
                 batch_size: int = 5, max_workers: int = 3,
                 my_merchant_name: str = ""):
        self.store_url        = store_url
        self.max_retries      = max_retries
        self.retry_delay      = retry_delay
        self.batch_size       = batch_size
        self.max_workers      = max_workers
        self.my_merchant_name = my_merchant_name.upper()
        self.merchant_id      = self._extract_merchant_id(store_url)

        # Alias listesi (örn: ["ESVENTO", "LAVAZZA ESVENTO"]) — controller'dan ayrıca set edilebilir
        self.my_merchant_aliases: List[str] = []
        if self.my_merchant_name:
            self.my_merchant_aliases = [self.my_merchant_name]

    def _normalize_merchant_text(self, text: str) -> str:
        if not text:
            return ""
        # Harf/rakam dışını boşluk yap, çoklu boşluğu tek boşluğa indir
        t = re.sub(r'[^0-9A-Za-zÇĞİÖŞÜçğıöşü]+', ' ', str(text))
        t = re.sub(r'\s+', ' ', t).strip().upper()
        return t

    def _is_my_merchant(self, seller_name: str) -> bool:
        if not seller_name:
            return False
        if not self.my_merchant_aliases and not self.my_merchant_name:
            return False
        normalized = self._normalize_merchant_text(seller_name)
        aliases = self.my_merchant_aliases or ([self.my_merchant_name] if self.my_merchant_name else [])
        for a in aliases:
            if not a:
                continue
            if self._normalize_merchant_text(a) in normalized:
                return True
        return False

    def _extract_merchant_id(self, url: str) -> Optional[str]:
        m = re.search(r'mid=(\d+)|merchantId=(\d+)', url)
        return (m.group(1) or m.group(2)) if m else None

    def _clean_product_url(self, url: str) -> str:
        """
        Tüm query string'i kaldır — sadece /ürün-adı-p-XXXXX kalsın.

        Neden önemli:
          Trendyol URL'de boutiqueId veya merchantId varsa O mağazanın
          fiyatını Buy Box olarak gösteriyor. Temiz URL açılınca gerçek
          Buy Box sahibi görünür.

        Örnek:
          /lavazza/rossa-p-123?boutiqueId=61&merchantId=1126746
          → https://www.trendyol.com/lavazza/rossa-p-123
        """
        clean = re.sub(r'\?.*$', '', url.strip())
        if clean.startswith('/'):
            clean = 'https://www.trendyol.com' + clean
        # http → https
        if clean.startswith('http://'):
            clean = 'https://' + clean[7:]
        return clean

    # ──────────────────────────────────────────────────────────────────────────
    # Ürün listesi (değişmedi)
    # ──────────────────────────────────────────────────────────────────────────

    def fetch_products(self) -> List[Dict]:
        return self.fetch_products_via_browser()

    def fetch_products_via_api(self) -> List[Dict]:
        return self.fetch_products_via_browser()

    def fetch_products_via_browser(self) -> List[Dict]:
        if not self.merchant_id:
            logger.error("❌ Merchant ID yok!")
            return []
        try:
            from playwright.sync_api import sync_playwright
            all_products, seen_ids = [], set()
            with sync_playwright() as p:
                browser, context = self._make_browser_context(p)
                page = context.new_page()
                url = f"https://www.trendyol.com/sr?mid={self.merchant_id}&os=1"
                page.goto(url, wait_until='domcontentloaded', timeout=60000)
                time.sleep(1.5)
                total = self._read_total_product_count(page)
                cards = self._scroll_until_all_loaded(page, total)
                for card in cards:
                    p_data = self._extract_product_from_card(card, seen_ids)
                    if p_data:
                        all_products.append(p_data)
                        seen_ids.add(p_data['id'])
                browser.close()
            logger.info(f"✅ {len(all_products)} ürün çekildi")
            return all_products
        except Exception as e:
            logger.error(f"❌ Ürün listesi hatası: {e}")
            return []

    def _read_total_product_count(self, page) -> int:
        try:
            body = page.text_content('body') or ''
            m = re.search(r'(\d+)\+?\s*[Üü]r[üu]n', body)
            return int(m.group(1)) if m else 0
        except:
            return 0

    def _scroll_until_all_loaded(self, page, total_expected: int = 0):
        last_count = no_new = 0
        max_no_new = 25  # Daha sabırlı

        for attempt in range(500):
            page.evaluate('window.scrollBy(0, 800)')  # Küçük adım — son kartları kaçırma
            time.sleep(1.2)

            if attempt % 3 != 0:
                no_new += 1
                if no_new >= max_no_new:
                    break
                continue

            cards = self._find_product_cards(page)
            cur = len(cards)
            if cur > last_count:
                logger.info(f"  📜 Scroll {attempt+1}: {cur} kart (+{cur-last_count})")
                last_count, no_new = cur, 0
                if total_expected > 0 and cur >= total_expected:
                    break
            else:
                no_new += 1
                try:
                    btn = page.query_selector('button:has-text("Daha Fazla")')
                    if btn and btn.is_visible():
                        btn.click(); time.sleep(2); no_new = 0; continue
                except:
                    pass
                if no_new >= max_no_new:
                    break

        # Son kartları yakalamak için ekstra bekle
        time.sleep(3)
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        time.sleep(2)
        final = self._find_product_cards(page)
        logger.info(f"  📦 Final kart sayısı: {len(final)}")
        return final

    def _find_product_cards(self, page) -> list:
        for sel in ['[class*="product-card"]', '[data-testid*="card"]',
                    '[data-testid*="product"]', '.p-card-wrppr']:
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
            for sel, attr in [
                ('self', 'href'), ('a[href*="boutiqueId"]', 'href'),
                ('a[href*="/p-"]', 'href'), ('a', 'href'),
            ]:
                if sel == 'self':
                    product_url = card.get_attribute('href')
                else:
                    link = card.query_selector(sel)
                    if link:
                        href = link.get_attribute(attr) or ''
                        if 'trendyol.com' in href or href.startswith('/'):
                            product_url = href
                if product_url:
                    break

            if not product_url:
                return None
            if product_url.startswith('/'):
                product_url = 'https://www.trendyol.com' + product_url

            pid_m = (re.search(r'-p-(\d+)', product_url) or
                     re.search(r'(?:contentId|productId)=(\d+)', product_url))
            if not pid_m:
                return None
            pid = pid_m.group(1)
            if pid in seen_ids:
                return None

            name = ''
            for sel in ['[class*="product-name"]', '[class*="prdct-desc"]', 'h2', 'h3']:
                e = card.query_selector(sel)
                if e:
                    n = e.text_content().strip()
                    if n and len(n) > 3:
                        name = n
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
            logger.warning(f"  ⚠️ Kart parse: {e}")
            return None

    # ──────────────────────────────────────────────────────────────────────────
    # Toplu satıcı çekme (batch)
    # ──────────────────────────────────────────────────────────────────────────

    def fetch_sellers_batch(self, products: List[Dict]) -> Dict[str, List[Dict]]:
        results = {}
        batches = [products[i:i+self.batch_size]
                   for i in range(0, len(products), self.batch_size)]
        logger.info(f"📦 {len(products)} ürün → {len(batches)} batch")

        for idx, batch in enumerate(batches):
            results.update(self._process_batch(batch))
            if (idx + 1) % 10 == 0:
                logger.info("  ⏸️  Kısa mola...")
                time.sleep(15)

        return results

    def _process_batch(self, batch: List[Dict]) -> Dict[str, List[Dict]]:
        from playwright.sync_api import sync_playwright
        results = {}
        with sync_playwright() as p:
            browser, context = self._make_browser_context(p)
            try:
                with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
                    futures = {
                        ex.submit(self.fetch_sellers_for_product,
                                  prod['url'], prod.get('name', ''), context): prod['id']
                        for prod in batch
                    }
                    for future in as_completed(futures):
                        pid = futures[future]
                        try:
                            results[pid] = future.result(timeout=90)
                        except Exception as e:
                            logger.error(f"  ❌ Ürün {pid}: {e}")
                            results[pid] = []
            finally:
                try:
                    browser.close()
                except:
                    pass
        return results

    # ──────────────────────────────────────────────────────────────────────────
    # Tek ürün satıcı çekme
    # ──────────────────────────────────────────────────────────────────────────

    def fetch_sellers_for_product(self, product_url: str, product_name: str = "",
                                   context=None) -> List[Dict]:
        try:
            clean_url = self._clean_product_url(product_url)
            sellers, actual_name = [], product_name

            logger.info(
                "  🔎 Ürün debug: clean_url=%s merchant_id=%s my_merchant_name=%s",
                clean_url,
                self.merchant_id,
                self.my_merchant_name,
            )

            own_browser = own_pw = None
            if context is None:
                from playwright.sync_api import sync_playwright
                own_pw = sync_playwright().start()
                own_browser, context = self._make_browser_context(own_pw)

            page = context.new_page()
            page.route("**/*.{png,jpg,jpeg,gif,webp,woff,woff2,ico,mp4,mp3}",
                       lambda route: route.abort())
            for t in ['googletagmanager', 'google-analytics', 'hotjar', 'facebook']:
                page.route(f"**/{t}**", lambda route: route.abort())

            try:
                loaded = False
                for attempt in range(self.max_retries):
                    try:
                        page.goto(clean_url, wait_until='domcontentloaded', timeout=90000)
                        time.sleep(1.5)
                        loaded = True
                        break
                    except Exception as e:
                        logger.warning(f"  ⚠️ Deneme {attempt+1}: {e}")
                        if attempt < self.max_retries - 1:
                            time.sleep(self.retry_delay)
                if not loaded:
                    return []

                for sel in ['.product-title', 'h1.pr-new-br', 'h1']:
                    e = page.query_selector(sel)
                    if e:
                        n = e.text_content().strip()
                        if n and len(n) > 5:
                            actual_name = n
                            break

                barcode = self._extract_barcode(page)

                buy_box = self._extract_buy_box_seller(page)
                if buy_box:
                    sellers.append(buy_box)
                    logger.info(f"  ✓ Buy Box: {buy_box['name']} — ₺{buy_box['net_price']} "
                                f"(liste=₺{buy_box['price']}, kupon={buy_box['coupon'] or '-'}, "
                                f"sepet={buy_box['basket_discount'] or '-'})")

                if self._open_other_sellers_panel(page):
                    mids = self._get_seller_merchant_urls(page, clean_url)
                    logger.info(
                        "  🧾 Panel merchantId URL listesi: %s",
                        [m.get('url') for m in (mids or [])],
                    )

                    # Panelde ESVENTO satırı var mı? (ekran görüntüsü gerekmesin)
                    if self.my_merchant_name:
                        try:
                            panel_text = (page.text_content('body') or '')
                            found_in_panel = self.my_merchant_name in panel_text.upper()
                            logger.info(
                                "  🧩 Panelde %s var mı?: %s",
                                self.my_merchant_name,
                                "EVET" if found_in_panel else "HAYIR",
                            )
                        except Exception as _pe:
                            logger.warning("  ⚠️ Panel metni okunamadı: %s", _pe)

                    if mids:
                        for mu in mids:
                            try:
                                logger.info("  ➜ Satıcı sayfasına gidiliyor: %s", mu.get('url'))
                                sp = context.new_page()
                                sp.route(
                                    "**/*.{png,jpg,jpeg,gif,webp,woff,woff2,ico,mp4,mp3}",
                                    lambda route: route.abort()
                                )
                                sp.goto(mu['url'], wait_until='domcontentloaded', timeout=60000)
                                time.sleep(1.2)

                                # merchantId sayfası gerçekten doğru yere mi gitti?
                                try:
                                    final_url = sp.url
                                except Exception:
                                    final_url = None

                                # Sadece kendi merchantId'miz için ekstra teşhis
                                if mu.get('mid') and self.merchant_id and str(mu.get('mid')) == str(self.merchant_id):
                                    try:
                                        body_snip = (sp.text_content('body') or '')[:3000]
                                        has_my_name = bool(self.my_merchant_name) and (self.my_merchant_name in body_snip.upper())
                                        logger.info(
                                            "  🧭 merchantId sayfası teşhis: expected_mid=%s final_url=%s body_has_%s=%s",
                                            self.merchant_id,
                                            final_url,
                                            self.my_merchant_name,
                                            has_my_name,
                                        )
                                    except Exception as _be:
                                        logger.warning(
                                            "  ⚠️ merchantId sayfası body okunamadı: expected_mid=%s final_url=%s err=%s",
                                            self.merchant_id,
                                            final_url,
                                            _be,
                                        )

                                sd = self._extract_buy_box_seller(sp)
                                if not sd:
                                    logger.warning(
                                        "  ⚠️ Satıcı sayfası buybox okunamadı: %s (final_url=%s)",
                                        mu.get('url'),
                                        final_url,
                                    )
                                else:
                                    logger.info(
                                        "  ↳ Satıcı sayfası buybox: name=%s price=%s net=%s url=%s",
                                        sd.get('name'), sd.get('price'), sd.get('net_price'), mu.get('url')
                                    )
                                sp.close()

                                if sd and sd['price'] > 0:
                                    name_lower = sd['name'].strip().lower()
                                    already = any(
                                        s['name'].strip().lower() == name_lower
                                        for s in sellers
                                    )
                                    if not already:
                                        sellers.append(sd)
                                        logger.info(
                                            f"  ✓ {sd['name']} — ₺{sd['net_price']} "
                                            f"(liste=₺{sd['price']}, kupon={sd['coupon'] or '-'}, "
                                            f"sepet={sd['basket_discount'] or '-'})"
                                        )
                            except Exception as _se:
                                logger.warning(f"  ⚠️ Satıcı sayfası: {_se} url={mu.get('url')}")
                    else:
                        others = self._parse_all_sellers_from_panel(page, buy_box)
                        sellers.extend(others)

                # ── Kendi mağazam eksikse merchantId URL ile tekrar ziyaret et ────
                if self.merchant_id and (self.my_merchant_name or self.my_merchant_aliases):
                    esvento_found = any(
                        self._is_my_merchant(s.get('name', ''))
                        for s in sellers
                    )
                    if not esvento_found:
                        try:
                            merchant_url = f"{clean_url}?merchantId={self.merchant_id}"
                            logger.info("  🔁 Kendi mağaza yok, merchantId ile tekrar: %s", merchant_url)
                            ep = context.new_page()
                            ep.route("**/*.{png,jpg,jpeg,gif,webp,woff,woff2,ico}",
                                     lambda r: r.abort())
                            ep.goto(merchant_url, wait_until='domcontentloaded', timeout=60000)
                            time.sleep(1.8)

                            # Redirect/engel teşhisi
                            try:
                                final_url = ep.url
                            except Exception:
                                final_url = None
                            try:
                                body_snip = (ep.text_content('body') or '')[:3000]
                                has_my_name = self.my_merchant_name in body_snip.upper()
                                logger.info(
                                    "  🧭 merchantId retry teşhis: final_url=%s body_has_%s=%s",
                                    final_url,
                                    self.my_merchant_name,
                                    has_my_name,
                                )
                            except Exception as _re:
                                logger.warning("  ⚠️ merchantId retry body okunamadı: %s", _re)

                            es = self._extract_buy_box_seller(ep)
                            ep.close()
                            if not es:
                                logger.warning("  ⚠️ merchantId ziyaretinde buybox okunamadı")
                            else:
                                logger.info(
                                    "  ↳ merchantId buybox: name=%s price=%s net=%s",
                                    es.get('name'), es.get('price'), es.get('net_price')
                                )
                            if es and self._is_my_merchant(es.get('name', '')):
                                sellers.append(es)
                                logger.info(
                                    f"  ✅ {es['name']} merchantId ziyareti ile eklendi: "
                                    f"₺{es['net_price']} (kupon={es['coupon'] or '-'})"
                                )
                            else:
                                logger.warning(
                                    "  ⚠️ merchantId ziyaretinde beklenen mağaza gelmedi. beklenen=%s gelen=%s",
                                    self.my_merchant_name,
                                    (es or {}).get('name') if isinstance(es, dict) else None,
                                )
                        except Exception as _me:
                            logger.warning(f"  ⚠️ Merchant URL ziyareti başarısız: {_me}")

                # ── Fiyat sanity check ──────────────────────────────────────
                # Kendi fiyatımızı bul
                my_price = 0.0
                for s in sellers:
                    if (self.my_merchant_name or self.my_merchant_aliases) and self._is_my_merchant(s.get('name', '')):
                        my_price = s['net_price']
                        break

                if my_price > 0:
                    for s in sellers:
                        if s.get('name', '').upper() == self.my_merchant_name:
                            continue
                        ratio = s['net_price'] / my_price
                        # Rakip fiyatı kendi fiyatımızın %40'ından ucuzsa şüpheli
                        if ratio < 0.40:
                            logger.warning(
                                f"  ⚠️ ŞÜPHELİ FİYAT: {s['name']} "
                                f"₺{s['net_price']} (benim: ₺{my_price}, oran: {ratio:.2f}) "
                                f"— ürün: {actual_name[:40]}"
                            )
                            s['suspicious'] = True

            finally:
                page.close()
                if own_browser:
                    own_browser.close()
                if own_pw:
                    own_pw.stop()

            for s in sellers:
                s['product_name'] = actual_name
                s['barcode'] = barcode

            logger.info(f"  ✅ {len(sellers)} satıcı: {[s['name'] for s in sellers]}")
            return sellers

        except Exception as e:
            logger.error(f"❌ Satıcı çekme hatası: {e}")
            return []

    def _extract_barcode(self, page) -> str:
        try:
            items = page.query_selector_all(
                'li[class*="content-description-item-description"], '
                '[data-testid="content-description-item-wrapper"]'
            )
            for item in items:
                text = item.text_content().strip()
                if 'barkod' in text.lower():
                    m = re.search(r'Barkod\s*No\s*[:\s]+([\w\-]+)', text, re.IGNORECASE)
                    if m:
                        return m.group(1)
        except:
            pass
        return ''

    # ──────────────────────────────────────────────────────────────────────────
    # Buy Box fiyat çekme
    # ──────────────────────────────────────────────────────────────────────────

    def _extract_buy_box_seller(self, page) -> Optional[Dict]:
        s = {
            'name': '', 'price': 0.0, 'old_price': 0.0,
            'coupon': '', 'coupon_max_tl': 0.0,
            'basket_discount': '', 'net_price': 0.0, 'rating': 0.0
        }
        try:
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

            # Buton metinlerini satıcı adı olarak kabul etme
            _INVALID = {'ürüne git', 'sepete ekle', 'satıcıya git',
                        'mağazaya git', 'kurumsal fatura', 'takip et kazan'}
            if s['name'].strip().lower() in _INVALID:
                return None

            for sel in ['.score-badge', '[class*="score-badge"]']:
                e = page.query_selector(sel)
                if e:
                    try:
                        s['rating'] = float(e.text_content().strip().replace(',', '.'))
                    except:
                        pass
                    break

            for sel in ['.prc-dsc', '.discounted', '[class*="prc-dsc"]',
                        '[class*="discounted"]', '.new-price', '.prc-box-dscntd']:
                e = page.query_selector(sel)
                if e:
                    p = parse_price(e.text_content())
                    if p > 0:
                        s['price'] = p
                        break

            for sel in ['.old-price', '.prc-org', '[class*="old-price"]']:
                e = page.query_selector(sel)
                if e:
                    p = parse_price(e.text_content())
                    if p > 0:
                        s['old_price'] = p
                        break

            coupon_info = self._extract_coupon_info(page)
            s['coupon']        = coupon_info['text']
            s['coupon_max_tl'] = coupon_info['max_tl']

            basket_info = self._extract_basket_info(page)
            s['basket_discount'] = basket_info['text']
            basket_net_price     = basket_info['net_price']

            s['net_price'] = compute_net_price(
                s['price'], s['coupon'], s['basket_discount'],
                basket_net_price, s['coupon_max_tl']
            )
            if s['net_price'] <= 0:
                s['net_price'] = s['price']

            # Log: fiyat katmanlarını açık yaz
            logger.debug(
                f"    💰 {s['name']}: liste=₺{s['price']} "
                f"kupon='{s['coupon']}' (max ₺{s['coupon_max_tl']}) "
                f"sepet='{s['basket_discount']}' "
                f"basket_net=₺{basket_net_price} → NET=₺{s['net_price']}"
            )

            return s if s['name'] and s['price'] > 0 else None

        except Exception as e:
            logger.warning(f"  ⚠️ Buy Box hatası: {e}")
            return None

    def _extract_coupon_info(self, page, elem=None) -> Dict:
        result = {'text': '', 'max_tl': 0.0}
        root = elem or page

        for sel in [
            '[data-testid="coupon-text"]', '.coupon-text',
            '[class*="coupon-text"]', '[class*="coupon"] span',
            '[class*="hit-coupon-container"] p[class*="coupon-text"]',
            '[class*="small-coupon-left"] p',
            'span:has-text("Kupon")',
        ]:
            try:
                e = root.query_selector(sel)
                if e:
                    text = e.text_content().strip()
                    if text and ('kupon' in text.lower() or '%' in text) and len(text) < 80:
                        result['text'] = text
                        break
            except:
                continue

        # Maks. İndirim limitini bul (ilk 5000 karakter ile sınırlı)
        try:
            body = (root.text_content() or '')[:5000]
            m = re.search(r'[Mm]aks\.?\s*[İi]ndirim\s*[:\s]+([\d.,]+)\s*TL', body)
            if m:
                result['max_tl'] = parse_price(m.group(1))
        except:
            pass

        return result

    def _extract_basket_info(self, page, elem=None) -> Dict:
        result = {'text': '', 'net_price': 0.0}
        root = elem or page

        # "Sepette X TL" direkt fiyat
        for sel in [
            '[class*="basket-price"]', '[class*="cart-price"]',
            'span[class*="prc"][class*="basket"]', 'span[class*="prc-grn"]',
            '[class*="campaign-price-wrapper"] .new-price',
            '[class*="campaign-price-content"] .new-price',
        ]:
            try:
                e = root.query_selector(sel)
                if e:
                    p = parse_price(e.text_content())
                    if p > 0:
                        result['net_price'] = p
                        break
            except:
                continue

        # DOM text tarama — "Sepette 1.596 TL" veya "Sepette 1.596,84 TL"
        if result['net_price'] == 0:
            try:
                body = (root.text_content() or '')[:5000]
                # Önce "Sepette X,XX TL" formatını dene (daha spesifik)
                m = re.search(r'[Ss]epette\s+([\d.]+,\d{2})\s*TL', body)
                if not m:
                    # Sonra "Sepette X TL" (tam sayı)
                    m = re.search(r'[Ss]epette\s+([\d.,]+)\s*TL', body)
                if m:
                    p = parse_price(m.group(1))
                    # Makul bir fiyat mı? (0 ile 100000 arası)
                    if 0 < p < 100000:
                        result['net_price'] = p
            except:
                pass

        # Sepet indirim metni
        for sel in [
            '[class*="basket-discount"]', '[class*="cart-discount"]',
            '[class*="sepette"]', 'span:has-text("Sepette %")',
            '[class*="info-text"]',
        ]:
            try:
                e = root.query_selector(sel)
                if e:
                    text = e.text_content().strip()
                    if text and 'sepette' in text.lower() and len(text) < 80:
                        result['text'] = text
                        break
            except:
                continue

        if not result['text']:
            try:
                body = (root.text_content() or '')[:5000]
                m = re.search(r'(Sepette\s+%\d+[^.\n]{0,30})', body)
                if m:
                    result['text'] = m.group(1).strip()
            except:
                pass

        return result

    # ──────────────────────────────────────────────────────────────────────────
    # Diğer satıcılar paneli
    # ──────────────────────────────────────────────────────────────────────────

    def _open_other_sellers_panel(self, page) -> bool:
        for sel in [
            '[data-testid="other-seller-button"]',
            'button:has-text("Diğer Satıcılar")',
            'a:has-text("Diğer Satıcılar")',
            '[class*="other-seller"] button',
            '[class*="seller-count"]',
        ]:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.scroll_into_view_if_needed()
                    btn.click()
                    try:
                        page.wait_for_selector(
                            '[data-testid="other-seller-item"], '
                            '.other-seller-item-total-container, '
                            '[class*="other-seller-item"]',
                            timeout=6000
                        )
                    except:
                        pass
                    return True
            except:
                continue
        return False

    def _parse_all_sellers_from_panel(self, page, buy_box: Optional[Dict]) -> List[Dict]:
        buy_box_name = (buy_box.get('name') or '').strip().lower() if buy_box else ''
        elems = self._find_panel_seller_elements(page)
        if not elems:
            return []

        sellers, seen = [], {buy_box_name}
        for elem in elems:
            try:
                seller = self._parse_single_seller_card(elem)
                if not seller or not seller.get('name') or seller['price'] <= 0:
                    continue
                name_lower = seller['name'].strip().lower()
                if name_lower in ('ürüne git', 'sepete ekle', 'satıcıya git'):
                    continue
                if name_lower in seen:
                    continue
                seen.add(name_lower)
                sellers.append(seller)
                logger.info(
                    f"  ✓ {seller['name']} — ₺{seller['net_price']} "
                    f"(liste=₺{seller['price']}, kupon={seller['coupon'] or '-'}, "
                    f"sepet={seller['basket_discount'] or '-'})"
                )
            except Exception as e:
                logger.warning(f"  ⚠️ Kart parse: {e}")
        return sellers

    def _get_seller_merchant_urls(self, page, clean_url: str) -> List[Dict]:
        """
        'Diğer Satıcılar' panelindeki her satıcının merchantId URL'ini çıkar.
        'Ürüne Git' butonlarının href'lerinden merchantId alınarak
        clean_url?merchantId=XXX formatında URL listesi döner.
        """
        merchant_urls = []
        seen_mids = set()
        try:
            # Önce merchantId içeren linkleri ara (en doğrudan yol)
            for link_sel in [
                'a[href*="merchantId="]',
                '[class*="other-seller-item"] a[href*="-p-"]',
                '[data-testid*="other-seller"] a[href*="-p-"]',
            ]:
                links = page.query_selector_all(link_sel)
                for link in links:
                    href = link.get_attribute('href') or ''
                    if not href:
                        continue
                    if href.startswith('/'):
                        href = 'https://www.trendyol.com' + href
                    mid_m = re.search(r'merchantId=(\d+)', href)
                    if mid_m:
                        mid = mid_m.group(1)
                        if mid not in seen_mids:
                            seen_mids.add(mid)
                            merchant_urls.append({
                                'mid': mid,
                                'url': f"{clean_url}?merchantId={mid}"
                            })
                if merchant_urls:
                    break

            if not merchant_urls:
                # Fallback: ürün ID'sine göre tüm linkleri tara
                pid_m = re.search(r'-p-(\d+)', clean_url)
                if pid_m:
                    all_links = page.query_selector_all(
                        f'a[href*="-p-{pid_m.group(1)}"]'
                    )
                    for link in all_links:
                        href = link.get_attribute('href') or ''
                        mid_m = re.search(r'merchantId=(\d+)', href)
                        if mid_m:
                            mid = mid_m.group(1)
                            if mid not in seen_mids:
                                seen_mids.add(mid)
                                merchant_urls.append({
                                    'mid': mid,
                                    'url': f"{clean_url}?merchantId={mid}"
                                })

        except Exception as e:
            logger.warning(f"  ⚠️ Merchant URL çıkarma hatası: {e}")

        if merchant_urls:
            logger.info(f"  🔗 {len(merchant_urls)} satıcı merchantId bulundu")
        return merchant_urls

    def _find_panel_seller_elements(self, page) -> list:
        for sel in [
            '[data-testid="other-seller-item"]',
            '.other-seller-item-total-container',
            '[class*="other-seller-item"]',
        ]:
            try:
                elems = page.query_selector_all(sel)
                if elems:
                    return elems
            except:
                continue

        try:
            seller_links = page.query_selector_all('a[href*="/sr?mid="]')
            containers, seen_mids = [], set()
            for link in seller_links:
                href = link.get_attribute('href') or ''
                mid_m = re.search(r'mid=(\d+)', href)
                if not mid_m or mid_m.group(1) in seen_mids:
                    continue
                seen_mids.add(mid_m.group(1))
                container = link.evaluate_handle(
                    'el => el.closest("[class*=\'other-seller-item\'],'
                    '[class*=\'seller-item\']") || '
                    'el.parentElement?.parentElement?.parentElement'
                )
                if container:
                    containers.append(container)
            if containers:
                return containers
        except:
            pass

        try:
            candidates = page.query_selector_all('div[class*="other-seller"]')
            return [d for d in candidates
                    if re.search(r'\d+[.,]\d+', d.text_content() or '')
                    and len((d.text_content() or '').strip()) > 10][:20]
        except:
            return []

    def _parse_single_seller_card(self, elem) -> Optional[Dict]:
        s = {
            'name': '', 'price': 0.0, 'old_price': 0.0,
            'coupon': '', 'coupon_max_tl': 0.0,
            'basket_discount': '', 'net_price': 0.0, 'rating': 0.0
        }

        for sel in ['.merchant-name', '[class*="merchant-name"]',
                    '[class*="seller-name"]', 'h3', 'h4']:
            e = elem.query_selector(sel)
            if e:
                name = e.text_content().strip()
                if 2 < len(name) < 80:
                    s['name'] = name
                    break

        if not s['name']:
            full = elem.text_content() or ''
            cleaned = re.sub(
                r'\d+[.,]\d+\s*TL|%\d+|Ürüne Git|Sepete Ekle|Satıcıya Git|'
                r'Sepette|Kupon|Kargo|İndirim|Hızlı|Teslimat|Bedava', '', full
            ).strip()
            if 2 < len(cleaned) < 60:
                s['name'] = cleaned

        for sel in ['[data-testid="current-price"]', '.prc-dsc', '.discounted',
                    '[class*="prc-dsc"]', 'span[class*="prc"]']:
            e = elem.query_selector(sel)
            if e:
                p = parse_price(e.text_content())
                if p > 0:
                    s['price'] = p
                    break

        if s['price'] <= 0:
            full_text = elem.text_content() or ''
            for m in re.findall(r'\b\d{1,5}[.,]\d{2,3}\b', full_text):
                val = parse_price(m)
                if 1 < val < 100000:
                    s['price'] = val
                    break

        for sel in ['.old-price', '[class*="old-price"]']:
            e = elem.query_selector(sel)
            if e:
                p = parse_price(e.text_content())
                if p > 0:
                    s['old_price'] = p
                    break

        for sel in ['[data-testid="seller-score"]', '.score-badge', '[class*="score-badge"]']:
            e = elem.query_selector(sel)
            if e:
                try:
                    r = float(e.text_content().strip().replace(',', '.'))
                    if r > 0:
                        s['rating'] = r
                        break
                except:
                    pass

        coupon_info = self._extract_coupon_info(None, elem=elem)
        # Elementin kendi text'inde kupon varsa bul
        if not coupon_info['text']:
            full = elem.text_content() or ''
            m = re.search(r'(%\d+\s+[İi]ndirimli\s+[Kk]upon[^.\n]{0,30})', full)
            if not m:
                m = re.search(r'(\d[\d.,]*\s*TL\s+[Kk]upon[^.\n]{0,30})', full)
            if m:
                coupon_info['text'] = m.group(1).strip()
            mx = re.search(r'[Mm]aks\.?\s*[İi]ndirim\s*[:\s]+([\d.,]+)\s*TL', full)
            if mx:
                coupon_info['max_tl'] = parse_price(mx.group(1))

        s['coupon']        = coupon_info['text']
        s['coupon_max_tl'] = coupon_info['max_tl']

        basket_info = self._extract_basket_info(None, elem=elem)
        s['basket_discount'] = basket_info['text']

        s['net_price'] = compute_net_price(
            s['price'], s['coupon'], s['basket_discount'],
            basket_info['net_price'], s['coupon_max_tl']
        )
        if s['net_price'] <= 0:
            s['net_price'] = s['price']

        return s if s['name'] and s['price'] > 0 else None

    def _make_browser_context(self, playwright):
        is_ci = os.getenv('CI', 'false').lower() == 'true'
        args = ['--disable-blink-features=AutomationControlled']
        if is_ci:
            args += [
                '--no-sandbox', '--disable-dev-shm-usage',
                '--disable-gpu', '--single-process',
            ]
        browser = playwright.chromium.launch(headless=is_ci, args=args)
        context = browser.new_context(
            user_agent=(
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/145.0.0.0 Safari/537.36'
            ),
            viewport={'width': 1920, 'height': 1080},
            locale='tr-TR',
            timezone_id='Europe/Istanbul',
        )
        return browser, context

    def initialize(self) -> bool:
        try:
            from playwright.sync_api import sync_playwright  # noqa
            return True
        except ImportError:
            import subprocess
            subprocess.check_call(['pip', 'install', 'playwright'])
            subprocess.check_call(['playwright', 'install', 'chromium'])
            return True

    def close(self) -> None:
        logger.info("✅ Scraper kapatıldı")
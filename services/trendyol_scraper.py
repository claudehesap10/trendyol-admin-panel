"""
Trendyol Scraper Servisi - Gerçek Veri Çekme
Trendyol mağazasından ürün ve satıcı verilerini çeker
"""
import logging
import re
from typing import List, Dict, Optional
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class TrendyolScraper:
    """Trendyol mağazasından veri çeker"""
    
    def __init__(self, store_url: str, max_retries: int = 3, retry_delay: int = 5):
        self.store_url = store_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.driver = None
        self.session = None
    
    def initialize(self) -> bool:
        """Scraper'ı başlat"""
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Chrome options
            options = webdriver.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            self.driver = webdriver.Chrome(options=options)
            logger.info("✅ Selenium WebDriver başlatıldı")
            return True
        except Exception as e:
            logger.error(f"❌ Scraper başlatma hatası: {e}")
            return False
    
    def fetch_products(self) -> List[Dict]:
        """Mağaza sayfasından ürünleri çek"""
        try:
            if not self.driver:
                logger.error("❌ WebDriver başlatılmamış")
                return []
            
            logger.info(f"🔍 Ürünler çekiliyor: {self.store_url}")
            self.driver.get(self.store_url)
            
            # Sayfanın yüklenmesini bekle
            time.sleep(3)
            
            from selenium.webdriver.common.by import By
            
            # Ürün linklerini bul
            product_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/p-']")
            products = []
            
            for link in product_links[:10]:  # İlk 10 ürün
                try:
                    href = link.get_attribute('href')
                    if href and '/p-' in href:
                        product_id = href.split('/p-')[-1].split('?')[0]
                        product_name = link.text.strip()
                        
                        if product_name and product_id:
                            products.append({
                                'id': product_id,
                                'name': product_name,
                                'url': href
                            })
                except Exception as e:
                    logger.warning(f"⚠️ Ürün çekme hatası: {e}")
                    continue
            
            logger.info(f"✅ {len(products)} ürün çekildi")
            return products
        except Exception as e:
            logger.error(f"❌ Ürün çekme hatası: {e}")
            return []
    
    def fetch_sellers_for_product(self, product_url: str) -> List[Dict]:
        """Bir ürün için tüm satıcıları çek"""
        try:
            if not self.driver:
                logger.error("❌ WebDriver başlatılmamış")
                return []
            
            logger.info(f"🔍 Satıcılar çekiliyor: {product_url}")
            self.driver.get(product_url)
            
            # Sayfanın yüklenmesini bekle
            time.sleep(2)
            
            from selenium.webdriver.common.by import By
            
            sellers = []
            
            # Satıcı kartlarını bul
            seller_cards = self.driver.find_elements(By.CSS_SELECTOR, "[data-testid='seller-card']")
            
            for card in seller_cards:
                try:
                    seller_data = self._parse_seller_card(card)
                    if seller_data:
                        sellers.append(seller_data)
                except Exception as e:
                    logger.warning(f"⚠️ Satıcı parse hatası: {e}")
                    continue
            
            # Eğer satıcı kartı bulunamazsa, alternatif yöntemle dene
            if not sellers:
                sellers = self._fetch_sellers_alternative(product_url)
            
            logger.info(f"✅ {len(sellers)} satıcı çekildi")
            return sellers
        except Exception as e:
            logger.error(f"❌ Satıcı çekme hatası: {e}")
            return []
    
    def _parse_seller_card(self, card) -> Optional[Dict]:
        """Satıcı kartını parse et"""
        try:
            from selenium.webdriver.common.by import By
            
            # Satıcı adı
            seller_name_elem = card.find_element(By.CSS_SELECTOR, "[data-testid='seller-name']")
            seller_name = seller_name_elem.text.strip()
            
            # Fiyat
            price_elem = card.find_element(By.CSS_SELECTOR, "[data-testid='price']")
            price_text = price_elem.text.strip()
            price = self._extract_price(price_text)
            
            # Rating
            rating_elem = card.find_elements(By.CSS_SELECTOR, "[data-testid='rating']")
            rating = 0.0
            if rating_elem:
                rating_text = rating_elem[0].text.strip()
                rating = self._extract_rating(rating_text)
            
            # Kupon
            coupon_elem = card.find_elements(By.CSS_SELECTOR, "[data-testid='coupon']")
            coupon = ""
            if coupon_elem:
                coupon = coupon_elem[0].text.strip()
            
            # Sepette indirim
            basket_discount_elem = card.find_elements(By.CSS_SELECTOR, "[data-testid='basket-discount']")
            basket_discount = ""
            if basket_discount_elem:
                basket_discount = basket_discount_elem[0].text.strip()
            
            # Net fiyat hesapla
            net_price = self._calculate_net_price(price, coupon, basket_discount)
            
            return {
                'name': seller_name,
                'price': price,
                'rating': rating,
                'coupon': coupon,
                'basket_discount': basket_discount,
                'net_price': net_price
            }
        except Exception as e:
            logger.warning(f"⚠️ Satıcı kartı parse hatası: {e}")
            return None
    
    def _fetch_sellers_alternative(self, product_url: str) -> List[Dict]:
        """Alternatif yöntemle satıcıları çek (DOM analizi)"""
        try:
            from selenium.webdriver.common.by import By
            
            sellers = []
            
            # Sayfadaki tüm metni al ve satıcı bilgilerini ara
            page_source = self.driver.page_source
            
            # Esvento, KAHVEDEBİZ, Mass Coffee gibi satıcıları ara
            seller_names = ['Esvento', 'KAHVEDEBİZ', 'Mass Coffee', 'KAHVEDEBIZ']
            
            for seller_name in seller_names:
                if seller_name in page_source:
                    # Satıcı adı bulundu, fiyat ve diğer bilgileri ara
                    try:
                        # Satıcı adını içeren öğeyi bul
                        seller_elem = self.driver.find_element(By.XPATH, f"//*[contains(text(), '{seller_name}')]")
                        
                        # Satıcı kartının parent'ını bul
                        seller_card = seller_elem.find_element(By.XPATH, "./ancestor::div[@data-testid='seller-card'] | ./ancestor::div[@class*='seller']")
                        
                        # Fiyat, rating, kupon vb. bilgileri çek
                        seller_data = self._parse_seller_card(seller_card)
                        if seller_data:
                            sellers.append(seller_data)
                    except Exception as e:
                        logger.warning(f"⚠️ {seller_name} çekme hatası: {e}")
                        continue
            
            return sellers
        except Exception as e:
            logger.warning(f"⚠️ Alternatif satıcı çekme hatası: {e}")
            return []
    
    def _extract_price(self, price_text: str) -> float:
        """Fiyat metninden sayıyı çıkar"""
        try:
            # "1.680 TL" -> 1680
            price_str = re.sub(r'[^\d,.]', '', price_text)
            price_str = price_str.replace('.', '').replace(',', '.')
            return float(price_str)
        except:
            return 0.0
    
    def _extract_rating(self, rating_text: str) -> float:
        """Rating metninden sayıyı çıkar"""
        try:
            # "9.6" -> 9.6
            rating_str = re.findall(r'\d+[.,]\d+', rating_text)
            if rating_str:
                return float(rating_str[0].replace(',', '.'))
            return 0.0
        except:
            return 0.0
    
    def _calculate_net_price(self, base_price: float, coupon: str, basket_discount: str) -> float:
        """Net fiyatı hesapla"""
        net_price = base_price
        
        # Kupon indirimini uygula
        if coupon:
            # "%1 İndirimli Kupon" -> 1
            coupon_percent = re.findall(r'%(\d+)', coupon)
            if coupon_percent:
                discount_percent = float(coupon_percent[0])
                net_price *= (1 - discount_percent / 100)
        
        # Sepette indirimini uygula
        if basket_discount:
            # "Sepette %10 İndirim" -> 10
            discount_percent = re.findall(r'%(\d+)', basket_discount)
            if discount_percent:
                discount_percent = float(discount_percent[0])
                net_price *= (1 - discount_percent / 100)
        
        return round(net_price, 2)
    
    def close(self) -> None:
        """Scraper'ı kapat"""
        if self.driver:
            self.driver.quit()
            logger.info("✅ Scraper kapatıldı")

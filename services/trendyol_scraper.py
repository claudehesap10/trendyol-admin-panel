"""
Trendyol Scraper Servisi - Gerçek Veri Çekme
Trendyol mağazasından ürün ve satıcı verilerini çeker
"""
import logging
import re
import json
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
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            
            # Chrome options - GitHub Actions için optimize edilmiş
            options = webdriver.ChromeOptions()
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            options.add_argument('--window-size=1920,1080')
            
            # ChromeDriver'ı başlat
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            logger.info("✅ Selenium WebDriver başlatıldı")
            return True
        except Exception as e:
            logger.error(f"❌ Scraper başlatma hatası: {e}")
            logger.info("⚠️ Fallback yöntemine geçiliyor (requests + BeautifulSoup)")
            return self._initialize_requests()
    
    def _initialize_requests(self) -> bool:
        """Requests + BeautifulSoup fallback yöntemi"""
        try:
            import requests
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            logger.info("✅ Requests session başlatıldı (Fallback)")
            return True
        except Exception as e:
            logger.error(f"❌ Requests başlatma hatası: {e}")
            return False
    
    def fetch_products(self) -> List[Dict]:
        """Mağaza sayfasından ürünleri çek"""
        try:
            logger.info(f"🔍 Ürünler çekiliyor: {self.store_url}")
            
            if self.driver:
                return self._fetch_products_selenium()
            elif self.session:
                return self._fetch_products_requests()
            else:
                logger.error("❌ Hiçbir scraping yöntemi kullanılamıyor")
                return []
        except Exception as e:
            logger.error(f"❌ Ürün çekme hatası: {e}")
            return []
    
    def _fetch_products_selenium(self) -> List[Dict]:
        """Selenium ile ürünleri çek"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            self.driver.get(self.store_url)
            
            # Sayfanın yüklenmesini bekle
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='/p-']")))
            
            time.sleep(2)
            
            # Ürün linklerini bul
            product_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/p-']")
            products = []
            
            for link in product_links[:5]:  # İlk 5 ürün
                try:
                    href = link.get_attribute('href')
                    if href and '/p-' in href:
                        product_id = href.split('/p-')[-1].split('?')[0]
                        product_name = link.text.strip()
                        
                        if product_name and product_id and len(product_name) > 3:
                            products.append({
                                'id': product_id,
                                'name': product_name,
                                'url': href
                            })
                except Exception as e:
                    logger.warning(f"⚠️ Ürün çekme hatası: {e}")
                    continue
            
            logger.info(f"✅ {len(products)} ürün çekildi (Selenium)")
            return products
        except Exception as e:
            logger.error(f"❌ Selenium ürün çekme hatası: {e}")
            return []
    
    def _fetch_products_requests(self) -> List[Dict]:
        """Requests ile ürünleri çek"""
        try:
            from bs4 import BeautifulSoup
            
            response = self.session.get(self.store_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            products = []
            
            # Ürün linklerini bul
            product_links = soup.find_all('a', href=re.compile(r'/p-'))
            
            for link in product_links[:5]:  # İlk 5 ürün
                try:
                    href = link.get('href', '')
                    if href and '/p-' in href:
                        product_id = href.split('/p-')[-1].split('?')[0]
                        product_name = link.get_text(strip=True)
                        
                        if product_name and product_id and len(product_name) > 3:
                            products.append({
                                'id': product_id,
                                'name': product_name,
                                'url': href
                            })
                except Exception as e:
                    logger.warning(f"⚠️ Ürün çekme hatası: {e}")
                    continue
            
            logger.info(f"✅ {len(products)} ürün çekildi (Requests)")
            return products
        except Exception as e:
            logger.error(f"❌ Requests ürün çekme hatası: {e}")
            return []
    
    def fetch_sellers_for_product(self, product_url: str) -> List[Dict]:
        """Bir ürün için TÜM satıcıları çek"""
        try:
            logger.info(f"🔍 Satıcılar çekiliyor")
            
            if self.driver:
                return self._fetch_sellers_selenium(product_url)
            elif self.session:
                return self._fetch_sellers_requests(product_url)
            else:
                logger.error("❌ Hiçbir scraping yöntemi kullanılamıyor")
                return []
        except Exception as e:
            logger.error(f"❌ Satıcı çekme hatası: {e}")
            return []
    
    def _fetch_sellers_selenium(self, product_url: str) -> List[Dict]:
        """Selenium ile TÜM satıcıları çek"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            self.driver.get(product_url)
            
            # Sayfanın yüklenmesini bekle
            wait = WebDriverWait(self.driver, 10)
            time.sleep(3)
            
            sellers = []
            page_source = self.driver.page_source
            
            # Sayfadaki tüm metin içeriğini al
            body_elem = self.driver.find_element(By.TAG_NAME, "body")
            page_text = body_elem.text
            
            # "Diğer Satıcılar" bölümünü bul
            if "Diğer Satıcılar" in page_text or "satıcı" in page_text.lower():
                # Tüm potansiyel satıcı öğelerini bul
                # Satıcı adı, fiyat, rating gibi bilgileri içeren tüm div'leri ara
                
                seller_containers = self.driver.find_elements(By.XPATH, 
                    "//*[contains(text(), 'TL') and contains(., '€')]//ancestor::div[contains(@class, 'seller') or contains(@class, 'card') or contains(@data-testid, 'seller')]"
                )
                
                # Alternatif: Tüm fiyat bilgisini içeren öğeleri ara
                if not seller_containers:
                    seller_containers = self.driver.find_elements(By.XPATH,
                        "//*[contains(text(), 'TL')]//ancestor::div[1]"
                    )
                
                # Tüm satıcı kartlarını dinamik olarak bul
                seller_data_list = self._extract_sellers_from_page(page_source, page_text)
                sellers.extend(seller_data_list)
            
            logger.info(f"✅ {len(sellers)} satıcı çekildi (Selenium)")
            return sellers
        except Exception as e:
            logger.error(f"❌ Selenium satıcı çekme hatası: {e}")
            return []
    
    def _fetch_sellers_requests(self, product_url: str) -> List[Dict]:
        """Requests ile TÜM satıcıları çek"""
        try:
            from bs4 import BeautifulSoup
            
            response = self.session.get(product_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = soup.get_text()
            page_source = response.text
            
            sellers = []
            
            # Sayfadaki tüm satıcı verilerini çek
            seller_data_list = self._extract_sellers_from_page(page_source, page_text)
            sellers.extend(seller_data_list)
            
            logger.info(f"✅ {len(sellers)} satıcı çekildi (Requests)")
            return sellers
        except Exception as e:
            logger.error(f"❌ Requests satıcı çekme hatası: {e}")
            return []
    
    def _extract_sellers_from_page(self, page_source: str, page_text: str) -> List[Dict]:
        """Sayfadan tüm satıcıları dinamik olarak çıkar"""
        sellers = []
        
        try:
            # JSON verilerini ara (Trendyol genelde JSON'da veri gönderir)
            json_patterns = [
                r'window\.__PRODUCT_DETAIL_APP_INITIAL_STATE__\s*=\s*({.*?});',
                r'<script[^>]*>({.*?"sellers".*?})</script>',
                r'{"sellers".*?}',
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, page_source, re.DOTALL)
                for match in matches:
                    try:
                        data = json.loads(match)
                        if isinstance(data, dict):
                            # Satıcıları ara
                            sellers_data = self._extract_sellers_from_json(data)
                            sellers.extend(sellers_data)
                    except:
                        pass
            
            # JSON bulunamazsa, DOM'dan çık
            if not sellers:
                sellers = self._extract_sellers_from_dom(page_text)
            
            return sellers
        except Exception as e:
            logger.warning(f"⚠️ Satıcı çıkarma hatası: {e}")
            return []
    
    def _extract_sellers_from_json(self, data: dict) -> List[Dict]:
        """JSON'dan satıcıları çıkar"""
        sellers = []
        
        def find_sellers_recursive(obj):
            if isinstance(obj, dict):
                # Satıcı bilgilerini ara
                if 'sellerName' in obj or 'name' in obj:
                    seller = {
                        'name': obj.get('sellerName') or obj.get('name', 'Bilinmiyor'),
                        'price': float(obj.get('price', 0)) if obj.get('price') else 0.0,
                        'rating': float(obj.get('rating', 0)) if obj.get('rating') else 0.0,
                        'coupon': obj.get('coupon', ''),
                        'basket_discount': obj.get('basketDiscount', ''),
                        'net_price': float(obj.get('netPrice', 0)) if obj.get('netPrice') else float(obj.get('price', 0))
                    }
                    if seller['name'] != 'Bilinmiyor':
                        sellers.append(seller)
                
                # Recursive olarak ara
                for value in obj.values():
                    find_sellers_recursive(value)
            
            elif isinstance(obj, list):
                for item in obj:
                    find_sellers_recursive(item)
        
        find_sellers_recursive(data)
        return sellers
    
    def _extract_sellers_from_dom(self, page_text: str) -> List[Dict]:
        """DOM metninden satıcıları çıkar (fallback)"""
        sellers = []
        
        # Fiyat ve satıcı adı kombinasyonlarını ara
        # "SatıcıAdı" + "Fiyat TL" + "Rating" gibi
        
        # Örnek: "Esvento 1.680 TL 9.6"
        pattern = r'([A-Za-zÇçĞğİıÖöŞşÜü\s]+?)\s+(\d{1,5}[.,]\d{3})\s+TL.*?(\d[.,]\d)'
        
        matches = re.findall(pattern, page_text)
        
        for match in matches:
            try:
                seller_name = match[0].strip()
                price_str = match[1].replace('.', '').replace(',', '.')
                rating_str = match[2].replace(',', '.')
                
                if len(seller_name) > 2 and len(seller_name) < 50:
                    seller = {
                        'name': seller_name,
                        'price': float(price_str),
                        'rating': float(rating_str),
                        'coupon': '',
                        'basket_discount': '',
                        'net_price': float(price_str)
                    }
                    
                    # Duplikat kontrol
                    if not any(s['name'] == seller['name'] for s in sellers):
                        sellers.append(seller)
            except:
                pass
        
        return sellers
    
    def close(self) -> None:
        """Scraper'ı kapat"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("✅ Scraper kapatıldı")
            except:
                pass

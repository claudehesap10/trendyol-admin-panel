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
            options.add_argument('--disable-web-resources')
            options.add_argument('--disable-extensions')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--start-maximized')
            
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
            
            for link in product_links[:10]:  # İlk 10 ürün
                try:
                    href = link.get('href', '')
                    if href and '/p-' in href:
                        product_id = href.split('/p-')[-1].split('?')[0]
                        product_name = link.get_text(strip=True)
                        
                        if product_name and product_id:
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
        """Bir ürün için tüm satıcıları çek"""
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
        """Selenium ile satıcıları çek"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            self.driver.get(product_url)
            
            # Sayfanın yüklenmesini bekle
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[data-testid*='seller']")))
            
            time.sleep(2)
            
            sellers = []
            page_source = self.driver.page_source
            
            # Bilinen satıcıları ara
            seller_names = ['Esvento', 'KAHVEDEBİZ', 'KAHVEDEBIZ', 'Mass Coffee', 'Resmi Mağaza']
            
            for seller_name in seller_names:
                if seller_name in page_source:
                    try:
                        # Satıcı adını içeren öğeyi bul
                        seller_elems = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{seller_name}')]")
                        
                        for elem in seller_elems:
                            try:
                                # Fiyat bilgisini bul
                                parent = elem.find_element(By.XPATH, "./ancestor::div[@class*='seller' or @data-testid*='seller']")
                                
                                # Fiyat
                                price_elem = parent.find_elements(By.XPATH, ".//*[contains(text(), 'TL')]")
                                price = 0.0
                                if price_elem:
                                    price_text = price_elem[0].text
                                    price = self._extract_price(price_text)
                                
                                # Rating
                                rating_elem = parent.find_elements(By.CSS_SELECTOR, "[data-testid*='rating']")
                                rating = 0.0
                                if rating_elem:
                                    rating_text = rating_elem[0].text
                                    rating = self._extract_rating(rating_text)
                                
                                seller_data = {
                                    'name': seller_name,
                                    'price': price,
                                    'rating': rating,
                                    'coupon': '',
                                    'basket_discount': '',
                                    'net_price': price
                                }
                                
                                if seller_data not in sellers:
                                    sellers.append(seller_data)
                            except:
                                pass
                    except Exception as e:
                        logger.warning(f"⚠️ {seller_name} çekme hatası: {e}")
            
            logger.info(f"✅ {len(sellers)} satıcı çekildi (Selenium)")
            return sellers
        except Exception as e:
            logger.error(f"❌ Selenium satıcı çekme hatası: {e}")
            return []
    
    def _fetch_sellers_requests(self, product_url: str) -> List[Dict]:
        """Requests ile satıcıları çek"""
        try:
            from bs4 import BeautifulSoup
            
            response = self.session.get(product_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            sellers = []
            
            # Bilinen satıcıları ara
            seller_names = ['Esvento', 'KAHVEDEBİZ', 'KAHVEDEBIZ', 'Mass Coffee', 'Resmi Mağaza']
            
            page_text = soup.get_text()
            
            for seller_name in seller_names:
                if seller_name in page_text:
                    # Satıcı adını içeren öğeyi bul
                    seller_elem = soup.find(string=re.compile(seller_name, re.IGNORECASE))
                    
                    if seller_elem:
                        try:
                            # Parent container'ı bul
                            parent = seller_elem.find_parent(class_=re.compile('seller', re.IGNORECASE))
                            
                            if parent:
                                # Fiyat bilgisini bul
                                price_text = parent.get_text()
                                price = self._extract_price(price_text)
                                
                                # Rating bilgisini bul
                                rating_text = parent.get_text()
                                rating = self._extract_rating(rating_text)
                                
                                seller_data = {
                                    'name': seller_name,
                                    'price': price,
                                    'rating': rating,
                                    'coupon': '',
                                    'basket_discount': '',
                                    'net_price': price
                                }
                                
                                if seller_data not in sellers:
                                    sellers.append(seller_data)
                        except:
                            pass
            
            logger.info(f"✅ {len(sellers)} satıcı çekildi (Requests)")
            return sellers
        except Exception as e:
            logger.error(f"❌ Requests satıcı çekme hatası: {e}")
            return []
    
    def _extract_price(self, price_text: str) -> float:
        """Fiyat metninden sayıyı çıkar"""
        try:
            # "1.680 TL" -> 1680
            price_str = re.sub(r'[^\d,.]', '', price_text)
            price_str = price_str.replace('.', '').replace(',', '.')
            return float(price_str) if price_str else 0.0
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
    
    def close(self) -> None:
        """Scraper'ı kapat"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("✅ Scraper kapatıldı")
            except:
                pass

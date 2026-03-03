"""
Trendyol Scraper Servisi - Cloudscraper ile Cloudflare Bypass
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
        self.scraper = None
    
    def initialize(self) -> bool:
        """Scraper'ı başlat"""
        try:
            import cloudscraper
            
            self.scraper = cloudscraper.create_scraper()
            logger.info("✅ Cloudscraper başlatıldı (Cloudflare bypass)")
            return True
        except ImportError:
            logger.warning("⚠️ Cloudscraper yüklü değil, yüklüyorum...")
            try:
                import subprocess
                subprocess.check_call(['pip', 'install', 'cloudscraper'])
                
                import cloudscraper
                self.scraper = cloudscraper.create_scraper()
                logger.info("✅ Cloudscraper yüklendi ve başlatıldı")
                return True
            except Exception as e:
                logger.error(f"❌ Cloudscraper kurulumu başarısız: {e}")
                return False
        except Exception as e:
            logger.error(f"❌ Scraper başlatma hatası: {e}")
            return False
    
    def fetch_products(self) -> List[Dict]:
        """Mağaza sayfasından ürünleri çek"""
        try:
            logger.info(f"🔍 Ürünler çekiliyor: {self.store_url}")
            
            if not self.scraper:
                logger.error("❌ Scraper başlatılmamış")
                return []
            
            # Sayfayı indir
            response = self.scraper.get(self.store_url, timeout=15)
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            products = []
            seen_ids = set()
            
            # Ürün linklerini bul
            product_links = soup.select('a[href*="/p-"]')
            
            logger.info(f"📦 {len(product_links)} ürün linki bulundu")
            
            for link in product_links[:10]:  # İlk 10 ürün
                try:
                    href = link.get('href', '')
                    if not href:
                        continue
                    
                    # Tam URL'ye dönüştür
                    if href.startswith('/'):
                        href = 'https://www.trendyol.com' + href
                    
                    # Ürün ID'sini çıkar
                    if '/p-' in href:
                        product_id = href.split('/p-')[-1].split('?')[0].split('/')[0]
                        
                        if product_id and product_id not in seen_ids:
                            product_name = link.get_text(strip=True)
                            
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
            
            logger.info(f"✅ {len(products)} benzersiz ürün çekildi")
            return products
        except Exception as e:
            logger.error(f"❌ Ürün çekme hatası: {e}")
            return []
    
    def fetch_sellers_for_product(self, product_url: str) -> List[Dict]:
        """Bir ürün için TÜM satıcıları çek"""
        try:
            logger.info(f"🔍 Satıcılar çekiliyor")
            
            if not self.scraper:
                logger.error("❌ Scraper başlatılmamış")
                return []
            
            # Ürün sayfasını yükle
            response = self.scraper.get(product_url, timeout=15)
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            page_source = response.text
            page_text = soup.get_text()
            
            sellers = []
            
            # JSON verilerini ara
            seller_data_list = self._extract_sellers_from_page(page_source, page_text)
            sellers.extend(seller_data_list)
            
            # Eğer JSON'dan bulunamazsa, DOM'dan çık
            if not sellers:
                sellers = self._extract_sellers_from_dom(soup)
            
            logger.info(f"✅ {len(sellers)} satıcı çekildi")
            return sellers
        except Exception as e:
            logger.error(f"❌ Satıcı çekme hatası: {e}")
            return []
    
    def _extract_sellers_from_page(self, page_source: str, page_text: str) -> List[Dict]:
        """Sayfadan tüm satıcıları dinamik olarak çıkar"""
        sellers = []
        
        try:
            # JSON verilerini ara
            json_patterns = [
                r'window\.__PRODUCT_DETAIL_APP_INITIAL_STATE__\s*=\s*({.*?});',
                r'"sellers"\s*:\s*\[({.*?})\]',
                r'<script[^>]*type="application/json"[^>]*>({.*?})</script>',
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, page_source, re.DOTALL)
                for match in matches:
                    try:
                        json_str = match
                        if not json_str.startswith('{'):
                            json_str = '{' + json_str
                        if not json_str.endswith('}'):
                            json_str = json_str + '}'
                        
                        data = json.loads(json_str)
                        if isinstance(data, dict):
                            sellers_data = self._extract_sellers_from_json(data)
                            sellers.extend(sellers_data)
                    except:
                        pass
            
            return sellers
        except Exception as e:
            logger.warning(f"⚠️ JSON satıcı çıkarma hatası: {e}")
            return []
    
    def _extract_sellers_from_json(self, data: dict) -> List[Dict]:
        """JSON'dan satıcıları çıkar"""
        sellers = []
        
        def find_sellers_recursive(obj, depth=0):
            if depth > 20:
                return
            
            if isinstance(obj, dict):
                if 'sellerName' in obj or ('name' in obj and 'price' in obj):
                    try:
                        seller_name = obj.get('sellerName') or obj.get('name', 'Bilinmiyor')
                        price = obj.get('price', 0)
                        
                        if isinstance(price, str):
                            price = float(re.sub(r'[^\d.,]', '', price).replace(',', '.'))
                        else:
                            price = float(price) if price else 0.0
                        
                        seller = {
                            'name': str(seller_name),
                            'price': price,
                            'rating': float(obj.get('rating', 0)) if obj.get('rating') else 0.0,
                            'coupon': str(obj.get('coupon', '')),
                            'basket_discount': str(obj.get('basketDiscount', '')),
                            'net_price': price
                        }
                        
                        if seller['name'] != 'Bilinmiyor' and seller['price'] > 0:
                            sellers.append(seller)
                    except:
                        pass
                
                for value in obj.values():
                    find_sellers_recursive(value, depth + 1)
            
            elif isinstance(obj, list):
                for item in obj:
                    find_sellers_recursive(item, depth + 1)
        
        find_sellers_recursive(data)
        return sellers
    
    def _extract_sellers_from_dom(self, soup) -> List[Dict]:
        """BeautifulSoup DOM'dan satıcıları çıkar"""
        sellers = []
        
        try:
            seller_containers = soup.find_all('div', class_=re.compile(r'seller|merchant|vendor', re.I))
            
            for container in seller_containers:
                try:
                    name_elem = container.find(['h3', 'h4', 'span', 'p'], class_=re.compile(r'name|seller', re.I))
                    seller_name = name_elem.get_text(strip=True) if name_elem else None
                    
                    price_elem = container.find(string=re.compile(r'\d+[.,]\d+\s*TL'))
                    price_text = price_elem if price_elem else None
                    
                    rating_elem = container.find(string=re.compile(r'\d[.,]\d'))
                    rating_text = rating_elem if rating_elem else None
                    
                    if seller_name and price_text:
                        try:
                            price = float(re.sub(r'[^\d.,]', '', str(price_text)).replace(',', '.'))
                            rating = float(re.sub(r'[^\d.,]', '', str(rating_text)).replace(',', '.')) if rating_text else 0.0
                            
                            seller = {
                                'name': seller_name,
                                'price': price,
                                'rating': rating,
                                'coupon': '',
                                'basket_discount': '',
                                'net_price': price
                            }
                            
                            if not any(s['name'] == seller['name'] for s in sellers):
                                sellers.append(seller)
                        except:
                            pass
                except:
                    pass
            
            return sellers
        except Exception as e:
            logger.warning(f"⚠️ DOM satıcı çıkarma hatası: {e}")
            return []
    
    def close(self) -> None:
        """Scraper'ı kapat"""
        logger.info("✅ Scraper kapatıldı")

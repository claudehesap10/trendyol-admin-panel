#!/usr/bin/env python3
"""
Trendyol Otomasyon Ana Controller
Tüm süreci yönetir
"""
import sys
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict

os.makedirs('logs', exist_ok=True)  # bunu ekle

# Logging konfigürasyonu
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/automation.log')
    ]
)
logger = logging.getLogger(__name__)

# Proje kütüphanelerini import et
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import Config
from services.trendyol_scraper import TrendyolScraper
from services.telegram_service import TelegramService
from services.price_monitor import PriceMonitor
from utils.excel_generator import ExcelGenerator
from utils.email_sender import EmailSender

class MainController:
    """Ana kontroller - tüm işlemleri yönetir"""
    
    def __init__(self):
        self.config = Config
        self.scraper = None
        self.telegram = None
        self.email_sender = None
        self.excel_gen = None
        self.price_monitor = None
        self.start_time = None
        self.report_path = None
    
    def run(self) -> bool:
        """Ana işlemi çalıştır"""
        try:
            self.start_time = datetime.now()
            logger.info("=" * 60)
            logger.info("🚀 Trendyol Otomasyon Başladı")
            logger.info("=" * 60)
            
            # Konfigürasyonu kontrol et
            if not self.config.validate():
                logger.error("❌ Konfigürasyon hatası")
                return False
            
            self.config.print_config()
            
            # Servisleri başlat
            if not self._initialize_services():
                return False
            
            # Taramayı başlat
            if not self._run_scan():
                return False
            
            # Başarı mesajı
            self._send_success_notification()
            
            logger.info("=" * 60)
            logger.info("✅ Trendyol Otomasyon Başarıyla Tamamlandı")
            logger.info("=" * 60)
            return True
        
        except Exception as e:
            logger.error(f"❌ Kritik hata: {e}")
            self._send_error_notification(str(e))
            return False
    
    def _initialize_services(self) -> bool:
        """Servisleri başlat"""
        try:
            logger.info("🔧 Servisleri başlatıyorum...")
            
            # Scraper
            self.scraper = TrendyolScraper(
                self.config.TRENDYOL_STORE_URL,
                max_retries=self.config.MAX_RETRIES,
                retry_delay=self.config.RETRY_DELAY
            )
            if not self.scraper.initialize():
                return False
            
            # Telegram
            self.telegram = TelegramService(
                self.config.TELEGRAM_BOT_TOKEN,
                self.config.TELEGRAM_CHAT_ID
            )
            
            # Email Sender
            self.email_sender = EmailSender()
            
            # Excel Generator
            self.excel_gen = ExcelGenerator(self.config.OUTPUT_DIR)
            
            # Price Monitor (Fiyat Takibi)
            if self.config.ENABLE_PRICE_ALERTS:
                self.price_monitor = PriceMonitor(
                    my_merchant_name=self.config.MY_MERCHANT_NAME,
                    price_threshold=self.config.PRICE_ALERT_THRESHOLD
                )
                logger.info(f"✅ Fiyat takibi aktif (Mağaza: {self.config.MY_MERCHANT_NAME})")
            
            logger.info("✅ Tüm servisleri başlatıldı")
            return True
        except Exception as e:
            logger.error(f"❌ Servis başlatma hatası: {e}")
            return False
    
    def _run_scan(self) -> bool:
        """Taramayı çalıştır"""
        try:
            logger.info("📊 Tarama başlanıyor...")
            
            # Başlangıç bildirimi gönder
            if self.telegram:
                if not self.telegram.send_start_notification():
                    logger.warning("⚠️ Başlangıç bildirimi gönderilemedi")
            
            # Ürünleri çek - Önce API ile dene
            logger.info("🔄 API ile tüm ürünler çekiliyor...")
            products = self.scraper.fetch_products_via_api()
            
            if not products:
                logger.warning("⚠️ Hiçbir ürün çekilemedi")
                return False
            
            logger.info(f"📦 {len(products)} benzersiz ürün çekildi")

            if self.config.TEST_LIMIT > 0:
                products = products[:self.config.TEST_LIMIT]
                logger.info(f"🧪 Test modu: ilk {self.config.TEST_LIMIT} ürün işlenecek")

            # Her ürün için satıcıları çek — browser bir kez açılır, tüm ürünlerde kullanılır
            products_with_sellers = []
            from playwright.sync_api import sync_playwright
            with sync_playwright() as pw:
                browser, context = self.scraper._make_browser_context(pw)
                try:
                    for i, product in enumerate(products, 1):
                        logger.info(f"[{i}/{len(products)}] İşleniyor: {product['name']}")
                        sellers = self.scraper.fetch_sellers_for_product(
                            product['url'],
                            product['name'],
                            context
                        )
                        product['sellers'] = sellers
                        products_with_sellers.append(product)
                        logger.info(f"  ✓ {len(sellers)} satıcı bulundu")
                finally:
                    browser.close()
            
            # Toplam istatistikler
            total_sellers = sum(len(p.get('sellers', [])) for p in products_with_sellers)
            logger.info("=" * 60)
            logger.info("📊 TARAMA ÖZETİ:")
            logger.info(f"   📦 Benzersiz Ürün: {len(products)}")
            logger.info(f"   🏪 Toplam Satıcı Kaydı: {total_sellers}")
            logger.info(f"   📈 Ortalama Satıcı/Ürün: {total_sellers/len(products):.1f}")
            logger.info("=" * 60)
            
            # Excel raporu oluştur
            report_path = self.excel_gen.generate_report(products_with_sellers)

            # Fiyat Değişim Raporu için Telegram/Mail bildirimlerini kaldırıldı.
            # (Rapor dosyası yine üretilir ve diskte saklanır.)
            self.report_path = report_path

            # 🔥 YENİ: Fiyat takibi ve uyarıları gönder
            if self.price_monitor:
                self._check_price_alerts(products_with_sellers)
            
            logger.info("✅ Tarama tamamlandı")
            return True
        
        except Exception as e:
            logger.error(f"❌ Tarama hatası: {e}")
            return False
    
    def _check_price_alerts(self, products_with_sellers: List[Dict]) -> None:
        """Fiyat uyarılarını ve avantajları kontrol et ve bildirim gönder"""
        try:
            logger.info("🔍 Fiyat analizi başlıyor...")
            
            # Ürün verilerini düzleştir (her satıcı için bir satır)
            flattened_data = []
            for product in products_with_sellers:
                product_name = product.get('name', '')
                product_url = product.get('url', '')
                
                for seller in product.get('sellers', []):
                    flattened_data.append({
                        'Ürün Adı': product_name,
                        'Link': product_url,
                        'Satıcı': seller.get('name', ''),
                        'Son Fiyat (TL)': seller.get('net_price', seller.get('price', 0)),
                        'Rating': seller.get('rating', 0.0)
                    })
            
            # Fiyat analizi yap
            alerts, advantages = self.price_monitor.analyze_products(flattened_data)
            
            # Özet oluştur
            summary = self.price_monitor.get_summary()
            logger.info(summary)

            # %5+ ucuz ürünler için aksiyon maili
            too_cheap_html = self.price_monitor.get_too_cheap_html()
            if too_cheap_html and self.email_sender:
                self.email_sender.send_html_email(
                    self.price_monitor.get_too_cheap_email_subject(),
                    too_cheap_html,
                )

            # (Telegram / diğer bildirim akışları burada intentionally yok)
            if alerts or advantages:
                logger.info(f"🔍 Analiz Sonucu: {len(alerts)} Uyarı, {len(advantages)} Avantaj tespit edildi.")
            else:
                logger.info("ℹ️ Özel durum yok, bildirim gönderilmedi")
            
        except Exception as e:
            logger.error(f"❌ Fiyat uyarı kontrol hatası: {e}")
    
    
    def _send_success_notification(self) -> None:
        """Başarı bildirimi gönder"""
        try:
            if self.telegram:
                elapsed_time = self._get_elapsed_time()
                if not self.telegram.send_message(
                    f"✅ <b>Tarama Başarıyla Tamamlandı</b>\n\n"
                    f"⏱️ Toplam Süre: {elapsed_time}"
                ):
                    logger.warning("⚠️ Başarı bildirimi gönderilemedi")
        except Exception as e:
            logger.error(f"❌ Başarı bildirimi gönderim hatası: {e}")
    
    def _send_error_notification(self, error: str) -> None:
        """Hata bildirimi gönder"""
        try:
            if self.telegram:
                if not self.telegram.send_error_notification(error):
                    logger.warning("⚠️ Hata bildirimi gönderilemedi")
        except Exception as e:
            logger.error(f"❌ Hata bildirimi gönderim hatası: {e}")
    
    def _get_elapsed_time(self) -> str:
        """Geçen zamanı hesapla"""
        if not self.start_time:
            return "Bilinmiyor"
        
        elapsed = datetime.now() - self.start_time
        minutes = elapsed.total_seconds() / 60
        return f"{minutes:.1f} dakika"
    
    def cleanup(self) -> None:
        """Kaynakları temizle"""
        try:
            if self.scraper:
                self.scraper.close()
            logger.info("✅ Kaynaklar temizlendi")
        except Exception as e:
            logger.error(f"❌ Temizleme hatası: {e}")

def main():
    """Ana giriş noktası"""
    controller = MainController()
    
    try:
        success = controller.run()
        sys.exit(0 if success else 1)
    finally:
        controller.cleanup()

if __name__ == "__main__":
    main()

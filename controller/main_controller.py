#!/usr/bin/env python3
"""
Trendyol Otomasyon Ana Controller
Tüm süreci yönetir
"""
import sys
import logging
from pathlib import Path
from datetime import datetime

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
            
            # Ürünleri çek
            products = self.scraper.fetch_products()
            if not products:
                logger.warning("⚠️ Hiçbir ürün çekilemedi")
                return False
            
            logger.info(f"📦 {len(products)} ürün çekildi")
            
            # Her ürün için satıcıları çek
            products_with_sellers = []
            for product in products:
                sellers = self.scraper.fetch_sellers_for_product(product['url'], product['name'])
                product['sellers'] = sellers
                products_with_sellers.append(product)
                logger.info(f"  ✓ {product['name']}: {len(sellers)} satıcı")
            
            # Excel raporu oluştur
            report_path = self.excel_gen.generate_report(products_with_sellers)
            
            # Raporu Telegram'a gönder (ZORUNLU)
            if self.telegram:
                scan_time = self._get_elapsed_time()
                total_sellers = sum(len(p.get('sellers', [])) for p in products_with_sellers)
                
                if not self.telegram.send_scan_report(report_path, total_sellers, scan_time):
                    logger.error("❌ Telegram'a rapor gönderilemedi!")
                    return False
            
            # Raporu email ile gönder
            self.report_path = report_path
            if self.email_sender:
                if self.email_sender.send_report(report_path):
                    logger.info("✅ Email gönderimi başarılı")
                else:
                    logger.warning("⚠️ Email gönderilemedi (opsiyonel)")
            
            logger.info("✅ Tarama tamamlandı")
            return True
        
        except Exception as e:
            logger.error(f"❌ Tarama hatası: {e}")
            return False
    
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

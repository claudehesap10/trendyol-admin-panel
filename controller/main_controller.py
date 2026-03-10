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
            
            # Her ürün için satıcıları çek
            products_with_sellers = []
            for i, product in enumerate(products, 1):
                logger.info(f"[{i}/{len(products)}] İşleniyor: {product['name']}")
                sellers = self.scraper.fetch_sellers_for_product(product['url'], product['name'])
                product['sellers'] = sellers
                products_with_sellers.append(product)
                logger.info(f"  ✓ {len(sellers)} satıcı bulundu")
            
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
            
            # Raporu Telegram'a gönder (ZORUNLU)
            if self.telegram:
                scan_time = self._get_elapsed_time()
                
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
            
            # Bildirim gönder
            if alerts or advantages:
                # Telegram'a bildirim gönder
                if self.telegram:
                    self._send_price_notifications_telegram(alerts, advantages, summary)
                
                # Email'e bildirim gönder
                if self.email_sender:
                    self._send_price_notifications_email(alerts, advantages)
            else:
                logger.info("ℹ️ Özel durum yok, bildirim gönderilmedi")
            
        except Exception as e:
            logger.error(f"❌ Fiyat kontrol hatası: {e}")
    
    def _send_price_notifications_telegram(self, alerts: List, advantages: List, summary: str) -> None:
        """Telegram'a fiyat bildirimlerini gönder (hem uyarı hem avantaj)"""
        try:
            # Önce özet gönder
            self.telegram.send_message(summary)
            
            # UYARILAR (Rakip bizden ucuz)
            if alerts:
                self.telegram.send_message(f"{'='*40}\n🔴 FİYAT UYARILARI\n{'='*40}")
                
                for i, alert in enumerate(alerts[:10], 1):  # Max 10 uyarı
                    message = str(alert)
                    self.telegram.send_message(message)
                    
                    import time
                    time.sleep(0.5)
                
                if len(alerts) > 10:
                    self.telegram.send_message(
                        f"ℹ️ Toplam {len(alerts)} uyarı var, ilk 10'u gösterildi.\n"
                        f"Detaylı rapor için email'i kontrol edin."
                    )
            
            # AVANTAJLAR (Biz rakipten ucuz)
            if advantages:
                self.telegram.send_message(f"\n{'='*40}\n✅ FİYAT AVANTAJLARI\n{'='*40}")
                
                for i, advantage in enumerate(advantages[:10], 1):  # Max 10 avantaj
                    message = str(advantage)
                    self.telegram.send_message(message)
                    
                    import time
                    time.sleep(0.5)
                
                if len(advantages) > 10:
                    self.telegram.send_message(
                        f"ℹ️ Toplam {len(advantages)} avantaj var, ilk 10'u gösterildi.\n"
                        f"Detaylı rapor için email'i kontrol edin."
                    )
            
            logger.info("✅ Telegram fiyat bildirimleri gönderildi")
        except Exception as e:
            logger.error(f"❌ Telegram bildirim hatası: {e}")
    
    def _send_price_notifications_email(self, alerts: List, advantages: List) -> None:
        """Email'e fiyat bildirimlerini gönder (hem uyarı hem avantaj)"""
        try:
            # HTML email içeriği oluştur
            html_summary = self.price_monitor.get_html_summary()
            
            # UYARILAR
            html_alerts = ""
            if alerts:
                html_alerts += '<h2 style="color: #d32f2f; border-bottom: 2px solid #d32f2f; padding-bottom: 10px; margin-top: 30px;">🔴 FİYAT UYARILARI ({} adet)</h2>'.format(len(alerts))
                for alert in alerts:
                    html_alerts += alert.to_html() + "\n"
            
            # AVANTAJLAR
            html_advantages = ""
            if advantages:
                html_advantages += '<h2 style="color: #2e7d32; border-bottom: 2px solid #2e7d32; padding-bottom: 10px; margin-top: 30px;">✅ FİYAT AVANTAJLARI ({} adet)</h2>'.format(len(advantages))
                for advantage in advantages:
                    html_advantages += advantage.to_html() + "\n"
            
            html_body = f"""
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 900px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
                    .footer {{ background-color: #f5f5f5; padding: 20px; text-align: center; margin-top: 30px; border-radius: 0 0 8px 8px; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1 style="margin: 0; font-size: 32px;">� Fiyat Karşılaştırma Raporu</h1>
                        <p style="margin: 15px 0 0 0; font-size: 16px; opacity: 0.9;">
                            Rakiplerinizle fiyat karşılaştırması ve rekabet analizi
                        </p>
                    </div>
                    
                    {html_summary}
                    
                    {html_alerts}
                    
                    {html_advantages}
                    
                    <div class="footer">
                        <p><strong>📌 Önemli Notlar:</strong></p>
                        <p style="margin: 10px 0;">
                            • � Uyarılar: Rakiplerin sizden daha ucuza sattığı ürünler<br>
                            • ✅ Avantajlar: Sizin rakiplerden daha ucuza sattığınız ürünler<br>
                            • 💡 Fiyatlarınızı düzenli kontrol ederek rekabetçi kalın!
                        </p>
                        <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                        <p style="color: #999;">
                            Bu rapor otomatik olarak oluşturulmuştur.<br>
                            Trendyol Fiyat Takip Sistemi - {datetime.now().strftime('%d.%m.%Y %H:%M')}
                        </p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            total_count = len(alerts) + len(advantages)
            subject = f"� Fiyat Raporu: {len(alerts)} Uyarı, {len(advantages)} Avantaj"
            
            if self.email_sender.send_html_email(subject, html_body):
                logger.info("✅ Email fiyat bildirimleri gönderildi")
            else:
                logger.warning("⚠️ Email fiyat bildirimleri gönderilemedi")
                
        except Exception as e:
            logger.error(f"❌ Email bildirim hatası: {e}")
    
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

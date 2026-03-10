"""
Email Gönderme Utility
Trendyol raporu email ile gönderir
"""
import logging
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailSender:
    """Email gönderir"""
    
    def __init__(self):
        from config.config import Config
        self.smtp_server = Config.SMTP_SERVER
        self.smtp_port = Config.SMTP_PORT
        self.sender_email = Config.SMTP_EMAIL
        self.sender_password = Config.SMTP_PASSWORD
        self.recipient_email = Config.RECIPIENT_EMAIL
    
    def send_report(self, report_path: str, subject: str = None) -> bool:
        """Raporu email ile gönder"""
        try:
            if not all([self.sender_email, self.sender_password, self.recipient_email]):
                logger.warning("⚠️ Email konfigürasyonu eksik (SMTP_EMAIL, SMTP_PASSWORD, RECIPIENT_EMAIL)")
                return False
            
            if not Path(report_path).exists():
                logger.error(f"❌ Rapor dosyası bulunamadı: {report_path}")
                return False
            
            # Email oluştur
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.recipient_email
            msg['Date'] = formatdate(localtime=True)
            msg['Subject'] = subject or f"Trendyol Satıcı Analiz Raporu - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Email gövdesi
            body = f"""
Merhaba,

Trendyol satıcı analiz raporu hazırlanmıştır.

📊 Rapor Detayları:
- Oluşturulma Tarihi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Dosya: {Path(report_path).name}

📋 Excel'de Bulacağınız:
1. Tarama Raporu - Tüm satıcılar (filtrelenebilir)
   - Ürün Adı, Satıcı, Fiyat, Kupon, Rating vb.
   - En ucuz fiyat: 🟢 Yeşil
   - En pahalı fiyat: 🔴 Kırmızı

2. Özet Analiz - Ürün başına en ucuz satıcı
   - Ürün Adı
   - En Ucuz Satıcı
   - Fiyat Farkı (TL ve %)

💡 İpuçları:
- Veri → Filtre ile ürün/satıcı filtrele
- Fiyata göre sırala
- Özet Analiz sayfasında karşılaştırma yap

Saygılarımızla,
Trendyol Scraper Bot
"""
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Raporu ekle
            attachment = MIMEBase('application', 'octet-stream')
            with open(report_path, 'rb') as attachment_file:
                attachment.set_payload(attachment_file.read())
            
            encoders.encode_base64(attachment)
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename= {Path(report_path).name}',
            )
            msg.attach(attachment)
            
            # Email gönder
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logger.info(f"✅ Email gönderildi: {self.recipient_email}")
            logger.info(f"   📎 Ek: {Path(report_path).name}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Email gönderme hatası: {e}")
            return False

    def send_buy_box_notification(self, product_name: str, product_url: str, competitor_name: str, competitor_price: float, my_price: float, price_difference: float) -> bool:
        """Buy Box bildirimi gönderir"""
        try:
            if not all([self.sender_email, self.sender_password, self.recipient_email]):
                logger.warning("⚠️ Email konfigürasyonu eksik (SMTP_EMAIL, SMTP_PASSWORD, RECIPIENT_EMAIL)")
                return False

            msg = MIMEMultipart()
            msg["From"] = self.sender_email
            msg["To"] = self.recipient_email
            msg["Date"] = formatdate(localtime=True)
            msg["Subject"] = f"🚨 Buy Box Uyarısı: {product_name}"

            body = f"""
Merhaba,

Trendyol'da bir ürününüz için Buy Box uyarısı aldınız!

Ürün Adı: {product_name}
Ürün Linki: {product_url}

Rakip Satıcı: {competitor_name}
Rakip Fiyatı: {competitor_price:.2f} TL
Sizin Fiyatınız: {my_price:.2f} TL
Fiyat Farkı: {price_difference:.2f} TL (Rakip sizden daha ucuz)

Hemen kontrol edin ve aksiyon alın!

Saygılarımızla,
Trendyol Scraper Bot
"""
            msg.attach(MIMEText(body, "plain", "utf-8"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)

            logger.info(f"✅ Buy Box email bildirimi gönderildi: {self.recipient_email}")
            return True
        except Exception as e:
            logger.error(f"❌ Buy Box email gönderim hatası: {e}")
            return False

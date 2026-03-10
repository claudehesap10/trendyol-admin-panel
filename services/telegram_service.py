"""
Telegram Bot Servisi
Raporları Telegram'a gönderir
"""
import os
import requests
from typing import Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class TelegramService:
    """Telegram bot ile haberleşme"""
    
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{token}"
    
    def send_message(self, text: str) -> bool:
        """Metin mesajı gönder"""
        try:
            url = f"{self.api_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Telegram mesajı gönderildi")
                return True
            else:
                logger.error(f"❌ Telegram hatası: {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Telegram gönderim hatası: {e}")
            return False
    
    def send_file(self, file_path: str, caption: str = "") -> bool:
        """Dosya gönder (Excel raporu vb.)"""
        try:
            if not os.path.exists(file_path):
                logger.error(f"❌ Dosya bulunamadı: {file_path}")
                return False
            
            url = f"{self.api_url}/sendDocument"
            
            with open(file_path, 'rb') as f:
                files = {'document': f}
                data = {
                    'chat_id': self.chat_id,
                    'caption': caption,
                    'parse_mode': 'HTML'
                }
                response = requests.post(url, files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"✅ Dosya gönderildi: {os.path.basename(file_path)}")
                return True
            else:
                logger.error(f"❌ Dosya gönderim hatası: {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Dosya gönderim hatası: {e}")
            return False
    
    def send_scan_report(self, report_path: str, product_count: int, scan_time: str) -> bool:
        """Tarama raporunu gönder"""
        try:
            caption = (
                f"📊 <b>Trendyol Tarama Raporu</b>\n\n"
                f"📦 Taranılan Ürün: {product_count}\n"
                f"⏱️ Tarama Süresi: {scan_time}\n"
                f"✅ Durum: Başarılı\n\n"
                f"📎 Rapor dosyası ektedir."
            )
            return self.send_file(report_path, caption)
        except Exception as e:
            logger.error(f"❌ Rapor gönderim hatası: {e}")
            return False
    
    def send_error_notification(self, error_message: str) -> bool:
        """Hata bildirimi gönder"""
        try:
            text = (
                f"❌ <b>Trendyol Tarama Hatası</b>\n\n"
                f"<code>{error_message}</code>\n\n"
                f"Lütfen logs'u kontrol edin."
            )
            return self.send_message(text)
        except Exception as e:
            logger.error(f"❌ Hata bildirimi gönderim hatası: {e}")
            return False

    def send_buy_box_notification(self, product_name: str, product_url: str, competitor_name: str, competitor_price: float, my_price: float, price_difference: float) -> bool:
        """Buy Box bildirimi gönderir"""
        try:
            text = (
                f"🚨 <b>BUY BOX UYARISI!</b> 🚨\n\n"
                f"Ürün Adı: <b>{product_name}</b>\n"
                f"Ürün Linki: <a href=\"{product_url}\">Trendyol Sayfası</a>\n\n"
                f"Rakip Satıcı: <b>{competitor_name}</b>\n"
                f"Rakip Fiyatı: <b>{competitor_price:.2f} TL</b>\n"
                f"Sizin Fiyatınız: {my_price:.2f} TL\n"
                f"Fiyat Farkı: <b>{price_difference:.2f} TL</b> (Rakip daha ucuz)\n\n"
                f"Hemen kontrol edin ve aksiyon alın!"
            )
            return self.send_message(text)
        except Exception as e:
            logger.error(f"❌ Buy Box bildirimi gönderim hatası: {e}")
            return False

    def send_start_notification(self) -> bool:
        """Tarama başlangıç bildirimi gönder"""
        try:
            text = (
                f"🚀 <b>Trendyol Taraması Başladı</b>\n\n"
                f"⏱️ Başlangıç: {self._get_current_time()}\n"
                f"Tarama tamamlandığında bilgilendirileceksiniz."
            )
            return self.send_message(text)
        except Exception as e:
            logger.error(f"❌ Başlangıç bildirimi gönderim hatası: {e}")
            return False
    
    @staticmethod
    def _get_current_time() -> str:
        """Mevcut zamanı döndür"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

"""
Trendyol Otomasyon Projesi - Konfigürasyon Dosyası
Ortam değişkenlerinden ayarları yükler
"""
import os
from typing import Optional
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

class Config:
    """Uygulama konfigürasyonu"""
    
    # Trendyol Ayarları
    TRENDYOL_STORE_URL: str = os.getenv(
        "TRENDYOL_STORE_URL",
        "https://www.trendyol.com/sr?mid=1126746&os=1"
    )
    MY_MERCHANT_ID: str = os.getenv("MY_MERCHANT_ID", "1126746") # Kendi mağazanızın Trendyol Merchant ID'si
    MY_MERCHANT_NAME: str = os.getenv("MY_MERCHANT_NAME", "Esvento") # Kendi mağazanızın Trendyol'daki adı (ör: "FIRMANIZ A.Ş.")
    
    # Telegram Ayarları
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")
    
    # Email Ayarları
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_EMAIL: str = os.getenv("SMTP_EMAIL", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    RECIPIENT_EMAIL: str = os.getenv("RECIPIENT_EMAIL", "")
    
    # GitHub Ayarları
    GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")
    GITHUB_REPO: Optional[str] = os.getenv("GITHUB_REPO")
    GITHUB_WORKFLOW_ID: Optional[str] = os.getenv("GITHUB_WORKFLOW_ID")
    
    # Tarama Ayarları
    SCAN_TIMEOUT: int = int(os.getenv("SCAN_TIMEOUT", "300"))  # 5 dakika
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: int = int(os.getenv("RETRY_DELAY", "5"))  # saniye
    
    # Çıktı Ayarları
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "reports")
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")
    
    # Debug Modu
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "false").lower() == "true"
    
    @classmethod
    def validate(cls) -> bool:
        """Gerekli ayarları kontrol et"""
        required_fields = [
            ("TRENDYOL_STORE_URL", cls.TRENDYOL_STORE_URL),
            ("TELEGRAM_BOT_TOKEN", cls.TELEGRAM_BOT_TOKEN),
            ("TELEGRAM_CHAT_ID", cls.TELEGRAM_CHAT_ID),
            ("MY_MERCHANT_ID", cls.MY_MERCHANT_ID),
            ("MY_MERCHANT_NAME", cls.MY_MERCHANT_NAME),
        ]
        
        missing = [name for name, value in required_fields if not value]
        
        if missing:
            print(f"❌ Eksik ayarlar: {', '.join(missing)}")
            return False
        
        return True
    
    @classmethod
    def print_config(cls) -> None:
        """Ayarları yazdır (hassas bilgileri gizle)"""
        print("=" * 50)
        print("📋 Trendyol Otomasyon Konfigürasyonu")
        print("=" * 50)
        print(f"🌐 Trendyol URL: {cls.TRENDYOL_STORE_URL[:50]}...")
        print(f"📱 Telegram Token: {cls.TELEGRAM_BOT_TOKEN[:10]}...***")
        print(f"💬 Telegram Chat ID: {cls.TELEGRAM_CHAT_ID}")
        print(f"🏪 Kendi Mağaza ID: {cls.MY_MERCHANT_ID}")
        print(f"🏪 Kendi Mağaza Adı: {cls.MY_MERCHANT_NAME}")
        print(f"⏱️  Tarama Timeout: {cls.SCAN_TIMEOUT}s")
        print(f"🔄 Max Retries: {cls.MAX_RETRIES}")
        print(f"📁 Çıktı Klasörü: {cls.OUTPUT_DIR}")
        print(f"🐛 Debug Modu: {cls.DEBUG_MODE}")
        print("=" * 50)

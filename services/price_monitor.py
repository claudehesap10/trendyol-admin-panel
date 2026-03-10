"""
Fiyat Takip Servisi - ByBox için fiyat karşılaştırması
Kendi mağazamızdan daha ucuza satan satıcıları tespit eder
VE bizim daha ucuz olduğumuz ürünleri de raporlar
"""
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PriceAlert:
    """Fiyat uyarısı bilgileri (Rakip bizden ucuz)"""
    product_name: str
    product_url: str
    my_price: float
    competitor_name: str
    competitor_price: float
    price_difference: float
    price_difference_percent: float
    
    def __str__(self) -> str:
        return (
            f"🔴 FİYAT UYARISI!\n\n"
            f"📦 Ürün: {self.product_name}\n"
            f"🔗 Link: {self.product_url}\n\n"
            f"💰 Sizin Fiyatınız: {self.my_price:.2f} ₺\n"
            f"🏪 Rakip: {self.competitor_name}\n"
            f"💸 Rakip Fiyatı: {self.competitor_price:.2f} ₺\n\n"
            f"📉 Fark: {self.price_difference:.2f} ₺ ({self.price_difference_percent:.1f}%) daha ucuz!\n"
            f"⚠️ Bu rakip sizden {self.price_difference:.2f} ₺ daha ucuza satıyor!"
        )
    
    def to_html(self) -> str:
        """HTML formatında uyarı"""
        return f"""
        <div style="background-color: #fff3cd; border: 2px solid #ff9800; border-radius: 8px; padding: 20px; margin: 10px 0; font-family: Arial, sans-serif;">
            <h2 style="color: #d32f2f; margin-top: 0;">🔴 FİYAT UYARISI!</h2>
            
            <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3 style="color: #333; margin-top: 0;">📦 Ürün Bilgisi</h3>
                <p style="font-size: 16px; margin: 5px 0;"><strong>{self.product_name}</strong></p>
                <p style="margin: 5px 0;">
                    <a href="{self.product_url}" style="color: #1976d2; text-decoration: none;">
                        🔗 Ürüne Git
                    </a>
                </p>
            </div>
            
            <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3 style="color: #333; margin-top: 0;">💰 Fiyat Karşılaştırması</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="background-color: #f5f5f5;">
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Sizin Fiyatınız</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd; text-align: right; font-size: 18px; color: #d32f2f;">
                            {self.my_price:.2f} ₺
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Rakip:</strong> {self.competitor_name}</td>
                        <td style="padding: 10px; border: 1px solid #ddd; text-align: right; font-size: 18px; color: #2e7d32;">
                            {self.competitor_price:.2f} ₺
                        </td>
                    </tr>
                    <tr style="background-color: #ffebee;">
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Fark</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd; text-align: right; font-size: 20px; font-weight: bold; color: #d32f2f;">
                            -{self.price_difference:.2f} ₺ ({self.price_difference_percent:.1f}%)
                        </td>
                    </tr>
                </table>
            </div>
            
            <div style="background-color: #ffcdd2; padding: 12px; border-radius: 5px; margin-top: 15px;">
                <p style="margin: 0; color: #c62828; font-weight: bold;">
                    ⚠️ Bu rakip sizden {self.price_difference:.2f} ₺ daha ucuza satıyor!
                </p>
            </div>
        </div>
        """


@dataclass
class PriceAdvantage:
    """Fiyat avantajı bilgileri (Biz rakipten ucuzuz)"""
    product_name: str
    product_url: str
    my_price: float
    competitor_name: str
    competitor_price: float
    price_difference: float
    price_difference_percent: float
    
    def __str__(self) -> str:
        return (
            f"✅ FİYAT AVANTAJI!\n\n"
            f"📦 Ürün: {self.product_name}\n"
            f"🔗 Link: {self.product_url}\n\n"
            f"💰 Sizin Fiyatınız: {self.my_price:.2f} ₺\n"
            f"🏪 Rakip: {self.competitor_name}\n"
            f"💸 Rakip Fiyatı: {self.competitor_price:.2f} ₺\n\n"
            f"📈 Fark: {self.price_difference:.2f} ₺ ({self.price_difference_percent:.1f}%)\n"
            f"🎉 {self.competitor_name}'dan {self.price_difference:.2f} ₺ daha ucuzsunuz!"
        )
    
    def to_html(self) -> str:
        """HTML formatında avantaj"""
        return f"""
        <div style="background-color: #e8f5e9; border: 2px solid #4caf50; border-radius: 8px; padding: 20px; margin: 10px 0; font-family: Arial, sans-serif;">
            <h2 style="color: #2e7d32; margin-top: 0;">✅ FİYAT AVANTAJI!</h2>
            
            <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3 style="color: #333; margin-top: 0;">📦 Ürün Bilgisi</h3>
                <p style="font-size: 16px; margin: 5px 0;"><strong>{self.product_name}</strong></p>
                <p style="margin: 5px 0;">
                    <a href="{self.product_url}" style="color: #1976d2; text-decoration: none;">
                        🔗 Ürüne Git
                    </a>
                </p>
            </div>
            
            <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3 style="color: #333; margin-top: 0;">💰 Fiyat Karşılaştırması</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="background-color: #f5f5f5;">
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Sizin Fiyatınız</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd; text-align: right; font-size: 18px; color: #2e7d32;">
                            {self.my_price:.2f} ₺
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Rakip:</strong> {self.competitor_name}</td>
                        <td style="padding: 10px; border: 1px solid #ddd; text-align: right; font-size: 18px; color: #d32f2f;">
                            {self.competitor_price:.2f} ₺
                        </td>
                    </tr>
                    <tr style="background-color: #e8f5e9;">
                        <td style="padding: 10px; border: 1px solid #ddd;"><strong>Avantaj</strong></td>
                        <td style="padding: 10px; border: 1px solid #ddd; text-align: right; font-size: 20px; font-weight: bold; color: #2e7d32;">
                            +{self.price_difference:.2f} ₺ ({self.price_difference_percent:.1f}%)
                        </td>
                    </tr>
                </table>
            </div>
            
            <div style="background-color: #c8e6c9; padding: 12px; border-radius: 5px; margin-top: 15px;">
                <p style="margin: 0; color: #1b5e20; font-weight: bold;">
                    🎉 Harika! {self.competitor_name}'dan {self.price_difference:.2f} ₺ daha ucuzsunuz!
                </p>
            </div>
        </div>
        """


class PriceMonitor:
    """Fiyat takip servisi"""
    
    def __init__(self, my_merchant_name: str, price_threshold: float = 0.01):
        """
        Args:
            my_merchant_name: Kendi mağaza ismimiz (case-insensitive)
            price_threshold: Minimum fiyat farkı (TL)
        """
        self.my_merchant_name = my_merchant_name.upper()
        self.price_threshold = price_threshold
        self.alerts: List[PriceAlert] = []  # Rakip bizden ucuz
        self.advantages: List[PriceAdvantage] = []  # Biz rakipten ucuz
    
    def analyze_products(self, products_data: List[Dict]) -> Tuple[List[PriceAlert], List[PriceAdvantage]]:
        """
        Ürünleri analiz et, hem uyarıları hem avantajları bul
        
        Args:
            products_data: Excel'den okunan ürün verileri
            
        Returns:
            (alerts, advantages) tuple'ı
        """
        logger.info("🔍 Fiyat analizi başlıyor...")
        logger.info(f"   📊 {len(products_data)} kayıt analiz edilecek")
        logger.info(f"   🏪 Kendi mağaza: {self.my_merchant_name}")
        
        self.alerts = []
        self.advantages = []
        
        # Ürünleri grupla (Ürün Adı'na göre)
        products_by_name: Dict[str, List[Dict]] = {}
        for item in products_data:
            product_name = item.get("Ürün Adı", "").strip()
            if not product_name:
                continue
            
            if product_name not in products_by_name:
                products_by_name[product_name] = []
            products_by_name[product_name].append(item)
        
        logger.info(f"   📦 {len(products_by_name)} benzersiz ürün bulundu")
        
        # Her ürün için fiyat karşılaştırması yap
        for product_name, sellers in products_by_name.items():
            self._analyze_product(product_name, sellers)
        
        logger.info(f"✅ Analiz tamamlandı:")
        logger.info(f"   🔴 {len(self.alerts)} fiyat uyarısı (Rakip daha ucuz)")
        logger.info(f"   ✅ {len(self.advantages)} fiyat avantajı (Siz daha ucuz)")
        
        return self.alerts, self.advantages
    
    def _analyze_product(self, product_name: str, sellers: List[Dict]) -> None:
        """Tek bir ürün için satıcıları karşılaştır"""
        
        # Kendi satıcımızı bul
        my_seller = None
        competitors = []
        
        for seller in sellers:
            seller_name = seller.get("Satıcı", "").strip().upper()
            price = seller.get("Son Fiyat (TL)", 0)
            
            try:
                price = float(price) if price else 0.0
            except:
                price = 0.0
            
            if price <= 0:
                continue
            
            # Kendi mağazamız mı?
            if self.my_merchant_name in seller_name or seller_name in self.my_merchant_name:
                my_seller = {
                    **seller,
                    "price": price
                }
            else:
                competitors.append({
                    **seller,
                    "price": price
                })
        
        # Kendi satıcımız yoksa bu ürünü atlayalım
        if not my_seller:
            return
        
        my_price = my_seller["price"]
        product_url = my_seller.get("Link", "")
        
        # Rakipleri kontrol et
        for competitor in competitors:
            competitor_price = competitor["price"]
            competitor_name = competitor.get("Satıcı", "Bilinmeyen Satıcı")
            
            price_diff = abs(my_price - competitor_price)
            
            # Eşik değerinden küçükse atla
            if price_diff < self.price_threshold:
                continue
            
            # Rakip bizden UCUZSA → UYARI
            if competitor_price < my_price:
                price_diff = my_price - competitor_price
                price_diff_percent = (price_diff / my_price) * 100
                
                alert = PriceAlert(
                    product_name=product_name,
                    product_url=product_url,
                    my_price=my_price,
                    competitor_name=competitor_name,
                    competitor_price=competitor_price,
                    price_difference=price_diff,
                    price_difference_percent=price_diff_percent
                )
                
                self.alerts.append(alert)
                logger.warning(f"   🔴 {product_name[:40]}... - {competitor_name} {price_diff:.2f}₺ daha ucuz!")
            
            # Biz rakipten UCUZSAK → AVANTAJ
            elif my_price < competitor_price:
                price_diff = competitor_price - my_price
                price_diff_percent = (price_diff / competitor_price) * 100
                
                advantage = PriceAdvantage(
                    product_name=product_name,
                    product_url=product_url,
                    my_price=my_price,
                    competitor_name=competitor_name,
                    competitor_price=competitor_price,
                    price_difference=price_diff,
                    price_difference_percent=price_diff_percent
                )
                
                self.advantages.append(advantage)
                logger.info(f"   ✅ {product_name[:40]}... - {competitor_name}'dan {price_diff:.2f}₺ ucuz!")
    
    def get_summary(self) -> str:
        """Özet rapor oluştur"""
        if not self.alerts and not self.advantages:
            return "ℹ️ Tüm fiyatlar eşit seviyede."
        
        summary = f"""
{'=' * 60}
📊 FİYAT KARŞILAŞTIRMA ÖZETİ
{'=' * 60}
"""
        
        # UYARILAR (Rakip bizden ucuz)
        if self.alerts:
            total_alerts = len(self.alerts)
            unique_products_alerts = len(set(alert.product_name for alert in self.alerts))
            avg_diff = sum(alert.price_difference for alert in self.alerts) / total_alerts
            max_diff = max(self.alerts, key=lambda x: x.price_difference)
            
            summary += f"""
� UYARILAR (Rakip Daha Ucuz):
   • Toplam Uyarı: {total_alerts}
   • Etkilenen Ürün: {unique_products_alerts}
   • Ortalama Fark: {avg_diff:.2f} ₺
   • En Yüksek Fark: {max_diff.price_difference:.2f} ₺
     ({max_diff.product_name[:30]}... vs {max_diff.competitor_name})
"""
        else:
            summary += f"\n🔴 UYARILAR: Yok (Rakip daha ucuz değil)\n"
        
        # AVANTAJLAR (Biz rakipten ucuz)
        if self.advantages:
            total_advantages = len(self.advantages)
            unique_products_advantages = len(set(adv.product_name for adv in self.advantages))
            avg_adv = sum(adv.price_difference for adv in self.advantages) / total_advantages
            max_adv = max(self.advantages, key=lambda x: x.price_difference)
            
            summary += f"""
✅ AVANTAJLAR (Siz Daha Ucuz):
   • Toplam Avantaj: {total_advantages}
   • Avantajlı Ürün: {unique_products_advantages}
   • Ortalama Avantaj: {avg_adv:.2f} ₺
   • En Yüksek Avantaj: {max_adv.price_difference:.2f} ₺
     ({max_adv.product_name[:30]}... vs {max_adv.competitor_name})
"""
        else:
            summary += f"\n✅ AVANTAJLAR: Yok (Rakipten ucuz değilsiniz)\n"
        
        summary += f"\n{'=' * 60}\n"
        return summary
    
    def get_html_summary(self) -> str:
        """HTML formatında özet rapor"""
        if not self.alerts and not self.advantages:
            return """
            <div style="background-color: #e3f2fd; border: 2px solid #2196f3; border-radius: 8px; padding: 20px; font-family: Arial, sans-serif;">
                <h2 style="color: #1565c0; margin-top: 0;">ℹ️ Fiyat Durumu</h2>
                <p style="font-size: 16px;">Tüm fiyatlar eşit seviyede. Özel durum yok.</p>
            </div>
            """
        
        html = ""
        
        # UYARILAR BÖLÜMÜ
        if self.alerts:
            total_alerts = len(self.alerts)
            unique_products = len(set(alert.product_name for alert in self.alerts))
            avg_diff = sum(alert.price_difference for alert in self.alerts) / total_alerts
            total_loss = sum(alert.price_difference for alert in self.alerts)
            
            html += f"""
            <div style="background-color: #ffebee; border: 2px solid #d32f2f; border-radius: 8px; padding: 20px; font-family: Arial, sans-serif; margin-bottom: 20px;">
                <h2 style="color: #d32f2f; margin-top: 0;">� FİYAT UYARILARI (Rakip Daha Ucuz)</h2>
                
                <table style="width: 100%; border-collapse: collapse; background-color: white; border-radius: 5px; overflow: hidden;">
                    <tr style="background-color: #f5f5f5;">
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">⚠️ Toplam Uyarı</td>
                        <td style="padding: 12px; border: 1px solid #ddd; text-align: right; font-size: 18px; color: #d32f2f;">
                            <strong>{total_alerts}</strong>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">📦 Etkilenen Ürün</td>
                        <td style="padding: 12px; border: 1px solid #ddd; text-align: right; font-size: 18px;">
                            {unique_products}
                        </td>
                    </tr>
                    <tr style="background-color: #f5f5f5;">
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">💰 Ortalama Fark</td>
                        <td style="padding: 12px; border: 1px solid #ddd; text-align: right; font-size: 18px;">
                            {avg_diff:.2f} ₺
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">📉 Toplam Potansiyel Kayıp</td>
                        <td style="padding: 12px; border: 1px solid #ddd; text-align: right; font-size: 20px; font-weight: bold; color: #d32f2f;">
                            {total_loss:.2f} ₺
                        </td>
                    </tr>
                </table>
                
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin-top: 15px; border-left: 4px solid #ff9800;">
                    <p style="margin: 0; color: #856404;">
                        💡 <strong>Öneri:</strong> Bu ürünlerde fiyat indirimi düşünebilirsiniz!
                    </p>
                </div>
            </div>
            """
        
        # AVANTAJLAR BÖLÜMÜ
        if self.advantages:
            total_advantages = len(self.advantages)
            unique_products = len(set(adv.product_name for adv in self.advantages))
            avg_adv = sum(adv.price_difference for adv in self.advantages) / total_advantages
            total_advantage = sum(adv.price_difference for adv in self.advantages)
            
            html += f"""
            <div style="background-color: #e8f5e9; border: 2px solid #4caf50; border-radius: 8px; padding: 20px; font-family: Arial, sans-serif; margin-bottom: 20px;">
                <h2 style="color: #2e7d32; margin-top: 0;">✅ FİYAT AVANTAJLARI (Siz Daha Ucuz)</h2>
                
                <table style="width: 100%; border-collapse: collapse; background-color: white; border-radius: 5px; overflow: hidden;">
                    <tr style="background-color: #f5f5f5;">
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">✅ Toplam Avantaj</td>
                        <td style="padding: 12px; border: 1px solid #ddd; text-align: right; font-size: 18px; color: #2e7d32;">
                            <strong>{total_advantages}</strong>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">📦 Avantajlı Ürün</td>
                        <td style="padding: 12px; border: 1px solid #ddd; text-align: right; font-size: 18px;">
                            {unique_products}
                        </td>
                    </tr>
                    <tr style="background-color: #f5f5f5;">
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">💰 Ortalama Avantaj</td>
                        <td style="padding: 12px; border: 1px solid #ddd; text-align: right; font-size: 18px;">
                            {avg_adv:.2f} ₺
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold;">📈 Toplam Rekabet Avantajı</td>
                        <td style="padding: 12px; border: 1px solid #ddd; text-align: right; font-size: 20px; font-weight: bold; color: #2e7d32;">
                            {total_advantage:.2f} ₺
                        </td>
                    </tr>
                </table>
                
                <div style="background-color: #c8e6c9; padding: 15px; border-radius: 5px; margin-top: 15px; border-left: 4px solid #4caf50;">
                    <p style="margin: 0; color: #1b5e20;">
                        🎉 <strong>Harika!</strong> Bu ürünlerde rakiplerinizden daha ucuzsunuz!
                    </p>
                </div>
            </div>
            """
        
        return html

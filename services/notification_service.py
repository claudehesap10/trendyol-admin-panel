import logging
from typing import List, Dict, Any
from services.telegram_service import TelegramService
from services.report_comparison_service import ReportComparisonService
from utils.email_sender import EmailSender

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, telegram_service: TelegramService, my_merchant_name: str = "Esvento"):
        self.telegram_service = telegram_service
        self.my_merchant_name = my_merchant_name
        self.comparison_service = ReportComparisonService()
        self.email_sender = EmailSender()

    def compare_and_notify(self) -> None:
        """Raporları karşılaştırır ve filtrelenmiş değişimleri bildirir"""
        try:
            logger.info("🔔 Bildirim servisi başlatıldı.")
            
            # 1. Raporları karşılaştır (tüm ürünleri al ki kendi ürünlerimizi bulabilelim)
            result = self.comparison_service.compare_latest_reports(only_changes=False)
            
            if "error" in result:
                logger.error(f"❌ Karşılaştırma hatası: {result['error']}")
                return
            
            all_changes = result.get("changes", [])
            summary = result.get("summary", {})
            
            if not all_changes:
                logger.info("ℹ️ Rapor verisi bulunmadı, bildirim gönderilmiyor.")
                return

            # 2. Benim ürünlerimi ve fiyatlarımı bul
            my_products_data = {
                c["product"]: c["new_price"] 
                for c in all_changes 
                if c["seller"] == self.my_merchant_name
            }
            
            my_products = set(my_products_data.keys())
            
            # 3. Filtreleme
            filtered_changes = {
                "buy_box_danger": [],
                "competitor_discount": [],
                "new_competitor": [],
                "opportunity": []
            }
            
            for change in all_changes:
                # Sadece değişim olanları (Sabit olmayanları) değerlendir
                if change["status"] == "Sabit":
                    continue

                product = change["product"]
                seller = change["seller"]
                status = change["status"]
                new_price = change["new_price"]
                
                # Sadece benim sattığım ürünler ve başkalarının yaptığı değişimler
                if product in my_products and seller != self.my_merchant_name:
                    if status == "İndirim":
                        my_price = my_products_data.get(product)
                        if my_price is not None and new_price < my_price:
                            filtered_changes["buy_box_danger"].append(change)
                        else:
                            filtered_changes["competitor_discount"].append(change)
                    elif status == "Yeni Satıcı":
                        filtered_changes["new_competitor"].append(change)
                    elif status == "Zam":
                        filtered_changes["opportunity"].append(change)

            # Herhangi bir değişim varsa gönder
            has_filtered_changes = any(filtered_changes.values())
            
            if has_filtered_changes:
                # 4. Telegram Mesajı Gönder
                self._send_telegram_notifications(filtered_changes, summary)
                
                # 5. Email Gönder
                self._send_email_notification(filtered_changes, summary)
            else:
                logger.info("ℹ️ Beni etkileyen değişim bulunmadı.")

        except Exception as e:
            logger.error(f"❌ Bildirim servisi genel hata: {e}")

    def _send_telegram_notifications(self, filtered_changes: Dict[str, List[Dict]], summary: Dict) -> None:
        """Filtrelenmiş değişimleri Telegram'a gönderir (split messages if needed)"""
        try:
            new_tag = summary.get("new_report", {}).get("tag", "N/A")
            old_tag = summary.get("old_report", {}).get("tag", "N/A")
            stats = summary.get("stats", {})
            
            header = f"🔔 <b>Fiyat Değişim Raporu</b>\n📊 {new_tag} ↔ {old_tag}\n\n"
            
            sections = []
            
            mapping = [
                ("buy_box_danger", "🔴 <b>Buy Box Tehlikesi</b>"),
                ("competitor_discount", "⚠️ <b>Rakip İndirim Yaptı</b>"),
                ("new_competitor", "🆕 <b>Yeni Rakip Geldi</b>"),
                ("opportunity", "🚀 <b>Fırsat: Rakip Zam Yaptı</b>")
            ]
            
            for key, title in mapping:
                items = filtered_changes[key]
                if items:
                    section = f"{title} ({len(items)})\n"
                    for item in items:
                        prod_name = item['product']
                        if len(prod_name) > 45:
                            prod_name = prod_name[:42] + "..."
                        
                        if key == "new_competitor":
                            line = f"• {prod_name} — {item['seller']} ₺{item['new_price']}\n"
                        else:
                            prefix = "+" if item['status'] == "Zam" else ""
                            line = (f"• {prod_name}\n"
                                   f"  {item['seller']} ₺{item['old_price'] or '?'} → ₺{item['new_price']} ({prefix}{item['percent']}%)\n")
                        section += line
                    sections.append(section)
            
            footer = (f"\n📈 Genel: İndirim {stats.get('İndirim', 0)} | "
                      f"Zam {stats.get('Zam', 0)} | "
                      f"Yeni Satıcı {stats.get('Yeni Satıcı', 0)} | "
                      f"Toplam {stats.get('Total', 0)}")
            
            # Telegram 4096 karakter limiti (güvenli sınır 4000)
            max_len = 4000
            
            if len(header + "\n".join(sections) + footer) <= max_len:
                self.telegram_service.send_message(header + "\n".join(sections) + footer)
            else:
                # Bölerek gönder
                current_msg = header
                for section in sections:
                    # Eğer mevcut mesaj + yeni section limiti aşıyorsa
                    if len(current_msg) + len(section) > max_len:
                        # Eğer section tek başına bile çok büyükse (nadiren olur) satır satır ekle
                        if len(section) > (max_len - 500):
                            lines = section.split("\n")
                            for line in lines:
                                if len(current_msg) + len(line) + 2 > max_len:
                                    self.telegram_service.send_message(current_msg)
                                    current_msg = "..." + line + "\n"
                                else:
                                    current_msg += line + "\n"
                        else:
                            # Mevcut mesajı gönder, yeniye geç
                            self.telegram_service.send_message(current_msg)
                            current_msg = section + "\n"
                    else:
                        current_msg += "\n" + section
                
                # Son parçayı gönder
                if current_msg:
                    self.telegram_service.send_message(current_msg + footer)
                
        except Exception as e:
            logger.error(f"❌ Telegram bildirim hatası: {e}")

    def _send_email_notification(self, filtered_changes: Dict[str, List[Dict]], summary: Dict) -> None:
        """Filtrelenmiş değişimleri HTML Mail olarak gönderir"""
        try:
            new_tag = summary.get("new_report", {}).get("tag", "N/A")
            old_tag = summary.get("old_report", {}).get("tag", "N/A")
            
            subject = f"🔔 Fiyat Değişim Raporu — {new_tag} ↔ {old_tag}"
            
            html_body = f"""
            <html>
                <body style="font-family: sans-serif; color: #333;">
                    <h2>📊 Fiyat Değişim Analizi</h2>
                    <p><b>Raporlar:</b> {new_tag} ↔ {old_tag}</p>
                    <hr/>
            """
            
            mapping = [
                ("buy_box_danger", "🔴 Buy Box Tehlikesi", "#dc2626"),
                ("competitor_discount", "⚠️ Rakip İndirim", "#d97706"),
                ("new_competitor", "🆕 Yeni Rakip", "#2563eb"),
                ("opportunity", "🚀 Fırsat", "#16a34a")
            ]
            
            for key, title, color in mapping:
                items = filtered_changes[key]
                if items:
                    html_body += f"""
                    <h3 style="color: {color}; border-bottom: 2px solid {color}; padding-bottom: 5px;">{title} ({len(items)})</h3>
                    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%; margin-bottom: 20px;">
                        <tr style="background-color: #f8f9fa;">
                            <th>Ürün Adı</th>
                            <th>Satıcı</th>
                            <th>Eski Fiyat</th>
                            <th>Yeni Fiyat</th>
                            <th>Değişim</th>
                        </tr>
                    """
                    for item in items:
                        prefix = "+" if item['status'] == "Zam" else ""
                        html_body += f"""
                        <tr>
                            <td>{item['product']}</td>
                            <td>{item['seller']}</td>
                            <td>₺{item['old_price'] or '-'}</td>
                            <td><b>₺{item['new_price']}</b></td>
                            <td style="color: {color}">{prefix}{item['percent']}%</td>
                        </tr>
                        """
                    html_body += "</table>"
            
            html_body += """
                    <p style="font-size: 0.8em; color: #666; margin-top: 30px;">
                        Bu e-posta otomatik olarak oluşturulmuştur.
                    </p>
                </body>
            </html>
            """
            
            self.email_sender.send_html_email(subject, html_body)
            
        except Exception as e:
            logger.error(f"❌ Email bildirim hatası: {e}")

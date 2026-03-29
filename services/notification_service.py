import logging
from typing import List, Dict, Any
from services.telegram_service import TelegramService
from services.report_comparison_service import ReportComparisonService
from services.price_monitor import PriceMonitor
from utils.email_sender import EmailSender

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, telegram_service: TelegramService, my_merchant_name: str = "Esvento"):
        self.telegram_service = telegram_service
        self.my_merchant_name = my_merchant_name
        self.comparison_service = ReportComparisonService()
        self.email_sender = EmailSender()
        # Fiyat Değişim Raporu Telegram/Mail bildirimleri kapalı
        self.notifications_enabled = False

    def compare_and_notify(self) -> None:
        """
        Raporları karşılaştırır.
        - notifications_enabled=False → Telegram/Mail gönderilmez
        - "Çok Ucuzsun" maili her zaman gönderilir (ayrı kontrol)
        """
        try:
            logger.info("🔔 Bildirim servisi başlatıldı.")

            # Her zaman karşılaştırmayı yap — "Çok Ucuzsun" maili için gerekli
            result = self.comparison_service.compare_latest_reports(only_changes=False)
            
            if "error" in result:
                logger.error(f"❌ Karşılaştırma hatası: {result['error']}")
                return
            
            all_changes = result.get("changes", [])
            summary = result.get("summary", {})
            
            if not all_changes:
                logger.info("ℹ️ Rapor verisi bulunamadı.")
                return

            # "Çok Ucuzsun" analizi — notifications_enabled'dan bağımsız
            self._check_and_send_too_cheap_alert(all_changes)

            # Fiyat değişim bildirimleri kapalıysa burada dur
            if not self.notifications_enabled:
                logger.info("ℹ️ Fiyat değişim bildirimleri devre dışı.")
                return

            # Kendi ürünlerim ve fiyatlarım
            my_products_data = {
                c["product"]: c["new_price"]
                for c in all_changes
                if c["seller"] == self.my_merchant_name
            }
            my_products = set(my_products_data.keys())

            filtered_changes = {
                "buy_box_danger": [],
                "competitor_discount": [],
                "new_competitor": [],
                "opportunity": []
            }

            for change in all_changes:
                if change["status"] == "Sabit":
                    continue

                product = change["product"]
                seller  = change["seller"]
                status  = change["status"]
                new_price = change["new_price"]

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

            if any(filtered_changes.values()):
                self._send_telegram_notifications(filtered_changes, summary)
                self._send_email_notification(filtered_changes, summary)
            else:
                logger.info("ℹ️ Beni etkileyen değişim yok.")

        except Exception as e:
            logger.error(f"❌ Bildirim servisi genel hata: {e}")

    def _check_and_send_too_cheap_alert(self, all_changes: List[Dict]) -> None:
        """
        PriceMonitor'ü kullanarak %5+ ucuz ürünleri tespit eder
        ve mail gönderir. notifications_enabled'dan bağımsız çalışır.
        """
        try:
            # all_changes listesini PriceMonitor'ün beklediği formata çevir
            products_data = [
                {
                    "Ürün Adı": c["product"],
                    "Ürün Linki": c.get("url", ""),
                    "Satıcı": c["seller"],
                    "Son Fiyat (TL)": c["new_price"],
                    "Barkod": c.get("barcode", ""),
                }
                for c in all_changes
            ]

            monitor = PriceMonitor(
                my_merchant_name=self.my_merchant_name,
                price_threshold=0.01
            )
            monitor.analyze_products(products_data)

            if monitor.too_cheap_advantages:
                logger.warning(
                    f"⚠️ {len(monitor.too_cheap_advantages)} ürünде %5+ ucuz tespit edildi — mail gönderiliyor"
                )
                subject = monitor.get_too_cheap_email_subject()
                html    = monitor.get_too_cheap_html()
                self.email_sender.send_html_email(subject, html)
            else:
                logger.info("✅ Çok ucuz ürün yok.")

        except Exception as e:
            logger.error(f"❌ Too-cheap kontrolü hatası: {e}")

    def _send_telegram_notifications(self, filtered_changes: Dict[str, List[Dict]],
                                      summary: Dict) -> None:
        """Filtrelenmiş değişimleri Telegram'a gönderir"""
        if not self.notifications_enabled:
            return
        try:
            new_tag = summary.get("new_report", {}).get("tag", "N/A")
            old_tag = summary.get("old_report", {}).get("tag", "N/A")
            stats   = summary.get("stats", {})

            header = f"🔔 <b>Fiyat Değişim Raporu</b>\n📊 {new_tag} ↔ {old_tag}\n\n"

            mapping = [
                ("buy_box_danger",      "🔴 <b>Buy Box Tehlikesi</b>"),
                ("competitor_discount", "⚠️ <b>Rakip İndirim Yaptı</b>"),
                ("new_competitor",      "🆕 <b>Yeni Rakip Geldi</b>"),
                ("opportunity",         "🚀 <b>Fırsat: Rakip Zam Yaptı</b>"),
            ]

            sections = []
            for key, title in mapping:
                items = filtered_changes[key]
                if not items:
                    continue
                section = f"{title} ({len(items)})\n"
                for item in items:
                    name = item['product'][:42] + "..." if len(item['product']) > 45 else item['product']
                    if key == "new_competitor":
                        section += (f"• <a href='{item['url']}'>{name}</a>\n"
                                    f"  Barkod: {item['barcode'] or '-'}\n"
                                    f"  Satıcı: {item['seller']} ₺{item['new_price']}\n")
                    else:
                        prefix = "+" if item['status'] == "Zam" else ""
                        section += (f"• <a href='{item['url']}'>{name}</a>\n"
                                    f"  Barkod: {item['barcode'] or '-'}\n"
                                    f"  {item['seller']} ₺{item['old_price'] or '?'} → "
                                    f"₺{item['new_price']} ({prefix}{item['percent']}%)\n")
                sections.append(section)

            footer = (f"\n📈 Genel: İndirim {stats.get('İndirim', 0)} | "
                      f"Zam {stats.get('Zam', 0)} | "
                      f"Yeni Satıcı {stats.get('Yeni Satıcı', 0)} | "
                      f"Toplam {stats.get('Total', 0)}")

            max_len = 4000
            full = header + "\n".join(sections) + footer

            if len(full) <= max_len:
                self.telegram_service.send_message(full)
            else:
                current = header
                for section in sections:
                    if len(current) + len(section) > max_len:
                        self.telegram_service.send_message(current)
                        current = section + "\n"
                    else:
                        current += "\n" + section
                if current:
                    self.telegram_service.send_message(current + footer)

        except Exception as e:
            logger.error(f"❌ Telegram bildirim hatası: {e}")

    def _send_email_notification(self, filtered_changes: Dict[str, List[Dict]],
                                  summary: Dict) -> None:
        """Filtrelenmiş değişimleri HTML Mail olarak gönderir"""
        if not self.notifications_enabled:
            return
        try:
            new_tag = summary.get("new_report", {}).get("tag", "N/A")
            old_tag = summary.get("old_report", {}).get("tag", "N/A")
            subject = f"🔔 Fiyat Değişim Raporu — {new_tag} ↔ {old_tag}"

            mapping = [
                ("buy_box_danger",      "🔴 Buy Box Tehlikesi",  "#dc2626"),
                ("competitor_discount", "⚠️ Rakip İndirim",      "#d97706"),
                ("new_competitor",      "🆕 Yeni Rakip",          "#2563eb"),
                ("opportunity",         "🚀 Fırsat",              "#16a34a"),
            ]

            html_body = f"""
            <html><body style="font-family:sans-serif;color:#333;">
            <h2>📊 Fiyat Değişim Analizi</h2>
            <p><b>Raporlar:</b> {new_tag} ↔ {old_tag}</p><hr/>
            """

            for key, title, color in mapping:
                items = filtered_changes[key]
                if not items:
                    continue
                rows = ""
                for item in items:
                    prefix = "+" if item['status'] == "Zam" else ""
                    rows += f"""
                    <tr>
                        <td>{item['product']}</td>
                        <td>{item.get('barcode') or '-'}</td>
                        <td>{item['seller']}</td>
                        <td>₺{item['old_price'] or '-'}</td>
                        <td><b>₺{item['new_price']}</b></td>
                        <td style="color:{color}">{prefix}{item['percent']}%</td>
                        <td><a href="{item['url']}">Git</a></td>
                    </tr>"""
                html_body += f"""
                <h3 style="color:{color};border-bottom:2px solid {color};padding-bottom:5px;">
                    {title} ({len(items)})
                </h3>
                <table border="1" cellpadding="8" cellspacing="0"
                       style="border-collapse:collapse;width:100%;margin-bottom:20px;">
                    <tr style="background:#f8f9fa;">
                        <th>Ürün</th><th>Barkod</th><th>Satıcı</th>
                        <th>Eski</th><th>Yeni</th><th>Değişim</th><th>Link</th>
                    </tr>
                    {rows}
                </table>"""

            html_body += """
            <p style="font-size:0.8em;color:#666;margin-top:30px;">
                Bu e-posta otomatik oluşturulmuştur.
            </p></body></html>"""

            self.email_sender.send_html_email(subject, html_body)

        except Exception as e:
            logger.error(f"❌ Email bildirim hatası: {e}")
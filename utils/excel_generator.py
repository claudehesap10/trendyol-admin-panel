"""
Excel Rapor Oluşturma Utility
Tarama sonuçlarını Excel dosyasına dönüştürür
"""
import logging
from typing import List, Dict
from datetime import datetime
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

logger = logging.getLogger(__name__)

class ExcelGenerator:
    """Excel rapor oluşturur"""
    
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate(self, filepath: str, data: List[Dict]) -> str:
        """Basit veri listesinden Excel oluştur"""
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Rapor"
            
            # Başlık satırı
            if data:
                headers = list(data[0].keys())
                for col, header in enumerate(headers, 1):
                    cell = ws.cell(row=1, column=col)
                    cell.value = header
                    cell.font = Font(bold=True, color="FFFFFF", size=11)
                    cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
                
                # Veri satırları
                for row_idx, item in enumerate(data, 2):
                    for col_idx, (key, value) in enumerate(item.items(), 1):
                        ws.cell(row=row_idx, column=col_idx).value = value
            
            # Dosyayı kaydet
            Path(filepath).parent.mkdir(exist_ok=True)
            wb.save(filepath)
            logger.info(f"✅ Excel raporu oluşturuldu: {filepath}")
            
            return filepath
        except Exception as e:
            logger.error(f"❌ Excel raporu oluşturma hatası: {e}")
            raise
    
    def generate_report(self, products_data: List[Dict], store_name: str = "Trendyol") -> str:
        """Rapor oluştur ve dosya yolunu döndür"""
        try:
            # Workbook oluştur
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Tarama Raporu"
            
            # Başlık ekle
            self._add_header(ws, store_name)
            
            # Veri ekle
            self._add_data(ws, products_data)
            
            # Dosyayı kaydet
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trendyol_report_{timestamp}.xlsx"
            filepath = self.output_dir / filename
            
            wb.save(str(filepath))
            logger.info(f"✅ Excel raporu oluşturuldu: {filepath}")
            
            return str(filepath)
        except Exception as e:
            logger.error(f"❌ Excel raporu oluşturma hatası: {e}")
            raise
    
    def _add_header(self, ws, store_name: str) -> None:
        """Başlık ekle"""
        # Başlık satırı
        ws['A1'] = f"Trendyol Satıcı Analiz Raporu - {store_name}"
        ws['A1'].font = Font(size=14, bold=True, color="FFFFFF")
        ws['A1'].fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        ws.merge_cells('A1:I1')
        ws['A1'].alignment = Alignment(horizontal="center", vertical="center")
        
        # Tarih bilgisi
        ws['A2'] = f"Rapor Tarihi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ws['A2'].font = Font(size=10, italic=True)
        
        # Sütun başlıkları
        headers = [
            "Ürün Adı",
            "Ürün Linki",
            "Satıcı",
            "Orijinal Fiyat (TL)",
            "Kupon İndirimi",
            "Sepette İndirimi",
            "Son Fiyat (TL)",
            "Rating",
            "Notlar"
        ]
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col)
            cell.value = header
            cell.font = Font(bold=True, color="FFFFFF", size=11)
            cell.fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    
    def _add_data(self, ws, products_data: List[Dict]) -> None:
        """Veri ekle"""
        row = 5
        
        for product in products_data:
            product_name = product.get('name', '')
            sellers = product.get('sellers', [])
            
            if not sellers:
                continue
            
            # Her satıcı için bir satır
            for idx, seller in enumerate(sellers):
                # Ürün adı (HER satıcı satırında)
                # Satıcıdan çekilmiş doğru adı kullan, yoksa varsayılan adı kullan
                actual_name = seller.get('product_name', product_name)
                ws.cell(row=row, column=1).value = actual_name
                
                # Ürün Linki
                ws.cell(row=row, column=2).value = product.get('url', '')
                
                # Satıcı adı
                ws.cell(row=row, column=3).value = seller.get('name', '')
                
                # Orijinal fiyat
                ws.cell(row=row, column=4).value = seller.get('price', 0)
                
                # Kupon İndirimi
                ws.cell(row=row, column=5).value = seller.get('coupon', '')
                
                # Sepette İndirimi
                ws.cell(row=row, column=6).value = seller.get('basket_discount', '')
                
                # Son Fiyat (Net Fiyat)
                ws.cell(row=row, column=7).value = seller.get('net_price', 0)
                
                # Rating
                ws.cell(row=row, column=8).value = seller.get('rating', 0)
                
                # Notlar
                notes = []
                if seller.get('coupon'):
                    notes.append(f"Kupon: {seller.get('coupon')}")
                if seller.get('basket_discount'):
                    notes.append(f"Sepette: {seller.get('basket_discount')}")
                ws.cell(row=row, column=9).value = ' | '.join(notes)
                
                # Hücre formatı
                for col in range(1, 10):
                    cell = ws.cell(row=row, column=col)
                    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                    cell.border = Border(
                        left=Side(style='thin'),
                        right=Side(style='thin'),
                        top=Side(style='thin'),
                        bottom=Side(style='thin')
                    )
                    
                    # Sayı formatı
                    if col in [4, 7, 8]:
                        cell.number_format = '0.00'
                
                row += 1
        
        # Sütun genişliği ayarla
        ws.column_dimensions['A'].width = 35
        ws.column_dimensions['B'].width = 50
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 18
        ws.column_dimensions['E'].width = 18
        ws.column_dimensions['F'].width = 18
        ws.column_dimensions['G'].width = 18
        ws.column_dimensions['H'].width = 12
        ws.column_dimensions['I'].width = 30

import pandas as pd
import httpx
import io
import logging
from typing import List, Dict, Any, Tuple
from utils.github_helper import GitHubHelper

logger = logging.getLogger(__name__)

class ReportComparisonService:
    """İki rapor arasındaki farkları analiz eden servis"""
    
    def __init__(self):
        self.github_helper = GitHubHelper()

    async def compare_latest_reports(self, only_changes: bool = True) -> Dict[str, Any]:
        """En güncel iki raporu karşılaştırır"""
        try:
            # 1. En güncel 2 raporun linklerini al
            reports = await self.github_helper.get_latest_reports(limit=2)
            
            if len(reports) < 2:
                logger.warning("⚠️ Karşılaştırma için en az 2 rapor gerekiyor.")
                return {"error": "Yetersiz rapor sayısı", "count": len(reports)}

            # En güncel (yeni) ve bir önceki (eski) rapor
            new_report_info = reports[0]
            old_report_info = reports[1]
            
            logger.info(f"📊 Karşılaştırılıyor: {new_report_info['tag']} vs {old_report_info['tag']}")

            # 2. Excel dosyalarını indir ve DataFrame'e oku
            df_new = await self._read_excel_from_url(new_report_info['download_url'])
            df_old = await self._read_excel_from_url(old_report_info['download_url'])

            if df_new is None or df_old is None:
                return {"error": "Excel dosyaları okunamadı"}

            # 3. Verileri karşılaştır
            comparison_results = self._process_comparison(df_new, df_old, only_changes=only_changes)
            
            return {
                "summary": {
                    "new_report": {
                        "tag": new_report_info['tag'],
                        "date": new_report_info['published_at']
                    },
                    "old_report": {
                        "tag": old_report_info['tag'],
                        "date": old_report_info['published_at']
                    },
                    "stats": comparison_results["stats"]
                },
                "changes": comparison_results["changes"]
            }

        except Exception as e:
            logger.error(f"❌ Rapor karşılaştırma hatası: {e}")
            return {"error": str(e)}

    async def _read_excel_from_url(self, url: str) -> pd.DataFrame:
        """URL'den Excel dosyasını indirip pandas DataFrame olarak döner"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                
                # io.BytesIO ile belleğe al
                excel_data = io.BytesIO(response.content)
                
                # Excel'i oku (Header 4. satırda, yani index 3)
                df = pd.read_excel(excel_data, skiprows=3)
                
                # Gerekli kolonları temizle ve hazırla
                required_cols = ["Ürün Adı", "Satıcı", "Son Fiyat (TL)"]
                for col in required_cols:
                    if col not in df.columns:
                        logger.error(f"❌ Eksik kolon: {col}")
                        return None
                
                # Veriyi temizle ve sadece gerekli kolonları al
                df = df[required_cols].dropna(subset=["Ürün Adı", "Satıcı"])
                
                # Veriyi tekilleştir (Mükerrer kayıtları temizle)
                df = df.drop_duplicates(subset=["Ürün Adı", "Satıcı"], keep="first")
                
                return df
                
        except Exception as e:
            logger.error(f"❌ Excel okuma hatası ({url}): {e}")
            return None

    def _process_comparison(self, df_new: pd.DataFrame, df_old: pd.DataFrame, only_changes: bool = True) -> Dict[str, Any]:
        """İki DataFrame'i karşılaştırır"""
        
        # Composite key oluştur (Ürün Adı + Satıcı)
        df_new['key'] = df_new['Ürün Adı'].astype(str) + "_" + df_new['Satıcı'].astype(str)
        df_old['key'] = df_old['Ürün Adı'].astype(str) + "_" + df_old['Satıcı'].astype(str)
        
        # Merge et (left join)
        merged = pd.merge(
            df_new, 
            df_old[['key', 'Son Fiyat (TL)']], 
            on='key', 
            how='left', 
            suffixes=('_yeni', '_eski')
        )
        
        changes = []
        stats = {
            "İndirim": 0,
            "Zam": 0,
            "Sabit": 0,
            "Yeni Satıcı": 0,
            "Total": len(merged)
        }
        
        for _, row in merged.iterrows():
            new_price = row['Son Fiyat (TL)_yeni']
            old_price = row['Son Fiyat (TL)_eski']
            
            status = "Sabit"
            diff = 0.0
            percent = 0.0
            
            if pd.isna(old_price):
                status = "Yeni Satıcı"
            else:
                diff = new_price - old_price
                if abs(diff) > 0.05: # 0.05 TL altı farkları kuruş oynaması diye sabit sayalım
                    percent = (diff / old_price) * 100
                    status = "Zam" if diff > 0 else "İndirim"
                else:
                    status = "Sabit"
                    diff = 0.0
                    percent = 0.0
            
            stats[status] += 1
            
            # Sadece değişimleri sakla (isteğe bağlı)
            if not only_changes or status != "Sabit":
                changes.append({
                    "product": row['Ürün Adı'],
                    "seller": row['Satıcı'],
                    "new_price": float(new_price),
                    "old_price": float(old_price) if not pd.isna(old_price) else None,
                    "diff": round(float(diff), 2),
                    "percent": round(float(percent), 2),
                    "status": status
                })
            
        return {
            "stats": stats,
            "changes": changes
        }
            
        return {
            "stats": stats,
            "changes": changes
        }

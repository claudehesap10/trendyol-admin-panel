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

    def compare_latest_reports(self, only_changes: bool = True) -> Dict[str, Any]:
        """En güncel iki raporu karşılaştırır"""
        try:
            reports = self.github_helper.get_latest_reports(limit=2)
            
            if len(reports) < 2:
                logger.warning("⚠️ Karşılaştırma için en az 2 rapor gerekiyor.")
                return {"error": "Yetersiz rapor sayısı", "count": len(reports)}

            new_report_info = reports[0]
            old_report_info = reports[1]
            
            logger.info(f"📊 Karşılaştırılıyor: {new_report_info['tag']} vs {old_report_info['tag']}")

            df_new = self._read_excel_from_url(new_report_info['download_url'])
            df_old = self._read_excel_from_url(old_report_info['download_url'])

            if df_new is None or df_old is None:
                return {"error": "Excel dosyaları okunamadı"}

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

    def _read_excel_from_url(self, url: str) -> pd.DataFrame:
        """URL'den Excel dosyasını indirip pandas DataFrame olarak döner"""
        try:
            headers = self.github_helper.headers.copy()
            # GitHub asset indirme için zorunlu
            headers["Accept"] = "application/octet-stream"
            
            with httpx.Client(follow_redirects=True, timeout=60.0) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                
                excel_data = io.BytesIO(response.content)
                
                # Header 4. satırda (index 3)
                df = pd.read_excel(excel_data, skiprows=3)
                
                logger.info(f"  📋 Excel sütunları: {list(df.columns)}")

                # Zorunlu sütunlar — excel_generator.py'deki gerçek isimlerle eşleşmeli
                required_cols = ["Ürün Adı", "Ürün Linki", "Satıcı", "Son Fiyat (TL)"]
                missing = [c for c in required_cols if c not in df.columns]
                if missing:
                    logger.error(f"❌ Eksik sütunlar: {missing}")
                    logger.error(f"   Mevcut sütunlar: {list(df.columns)}")
                    return None
                
                # Barkod eski raporlarda olmayabilir
                if "Barkod" not in df.columns:
                    df["Barkod"] = ""
                
                final_cols = required_cols + ["Barkod"]
                df = df[final_cols].dropna(subset=["Ürün Adı", "Satıcı"])
                df = df.drop_duplicates(subset=["Ürün Adı", "Satıcı"], keep="first")
                
                logger.info(f"  ✅ {len(df)} satır okundu")
                return df
                
        except Exception as e:
            logger.error(f"❌ Excel okuma hatası ({url}): {e}")
            return None

    def _process_comparison(self, df_new: pd.DataFrame, df_old: pd.DataFrame,
                             only_changes: bool = True) -> Dict[str, Any]:
        """İki DataFrame'i karşılaştırır"""
        
        df_new = df_new.copy()
        df_old = df_old.copy()

        df_new['key'] = df_new['Ürün Adı'].astype(str) + "_" + df_new['Satıcı'].astype(str)
        df_old['key'] = df_old['Ürün Adı'].astype(str) + "_" + df_old['Satıcı'].astype(str)
        
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
                try:
                    new_price = float(new_price)
                    old_price = float(old_price)
                except (ValueError, TypeError):
                    status = "Sabit"
                else:
                    diff = new_price - old_price
                    if abs(diff) > 0.05:
                        percent = (diff / old_price) * 100
                        status = "Zam" if diff > 0 else "İndirim"
                    else:
                        diff = 0.0
            
            stats[status] += 1
            
            if not only_changes or status != "Sabit":
                changes.append({
                    "product": row['Ürün Adı'],
                    "barcode": row.get('Barkod', ''),
                    # Düzeltme: sütun adı "Ürün Linki" — "Link" değil
                    "url": row.get('Ürün Linki', ''),
                    "seller": row['Satıcı'],
                    "new_price": float(new_price) if not pd.isna(new_price) else 0.0,
                    "old_price": float(old_price) if not pd.isna(old_price) else None,
                    "diff": round(float(diff), 2),
                    "percent": round(float(percent), 2),
                    "status": status
                })
            
        return {"stats": stats, "changes": changes}
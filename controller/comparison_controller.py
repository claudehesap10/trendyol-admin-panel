from fastapi import APIRouter, HTTPException
import logging
from services.report_comparison_service import ReportComparisonService

logger = logging.getLogger(__name__)

# FastAPI router oluştur
router = APIRouter(prefix="/api/reports", tags=["reports"])
comparison_service = ReportComparisonService()

@router.get("/compare")
async def compare_reports(show_all: bool = False):
    """
    GitHub Releases üzerindeki son iki raporu karşılaştırır ve 
    fiyat değişimlerini döner.
    
    show_all=True yapılırsa sabit ürünler de listeye dahil edilir.
    """
    try:
        logger.info(f"GET /api/reports/compare çağrıldı (show_all={show_all})")
        results = comparison_service.compare_latest_reports(only_changes=not show_all)
        
        if "error" in results:
            # İş mantığı hatası (örn: yetersiz rapor)
            if results.get("error") == "Yetersiz rapor sayısı":
                return {
                    "success": False,
                    "message": "Karşılaştırma yapmak için GitHub üzerinde en az 2 rapor (release) bulunmalıdır.",
                    "data": results
                }
            
            raise HTTPException(status_code=500, detail=results["error"])
            
        return {
            "success": True,
            "data": results
        }
        
    except Exception as e:
        logger.error(f"❌ ComparisonController hata: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Not: Bu router'ın ana FastAPI uygulamasında (app.include_router) 
# kaydedilmesi gerekir.

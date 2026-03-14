from fastapi import FastAPI
import uvicorn
from controller.comparison_controller import router as comparison_router
import logging

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Trendyol Price Comparison Test API")

# Router'ı dahil et
app.include_router(comparison_router)

@app.get("/")
async def root():
    return {"message": "Trendyol Price Comparison API is running"}

if __name__ == "__main__":
    logger.info("Test server başlatılıyor...")
    uvicorn.run(app, host="0.0.0.0", port=8000)

import httpx
import logging
import os
from typing import List, Dict, Optional
from config.config import Config

logger = logging.getLogger(__name__)

class GitHubHelper:
    """GitHub API işlemlerini yöneten yardımcı sınıf"""
    
    def __init__(self, token: Optional[str] = None, repo: Optional[str] = None):
        self.token = token or Config.GITHUB_TOKEN
        self.repo = repo or os.getenv("GITHUB_REPO", "claudehesap10/trendyol-admin-panel")
        self.base_url = f"https://api.github.com/repos/{self.repo}"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def get_latest_reports(self, limit: int = 2) -> List[Dict]:
        """
        En güncel release'leri çekip içindeki Excel dosyalarını bulur.
        
        Returns:
            List[Dict]: [
                {
                    "tag": "v1.0.0",
                    "published_at": "2024-01-01...",
                    "download_url": "...",
                    "filename": "..."
                },
                ...
            ]
        """
        try:
            url = f"{self.base_url}/releases"
            with httpx.Client() as client:
                response = client.get(url, headers=self.headers)
                response.raise_for_status()
                
                releases = response.json()
                # Draft olmayan en güncel release'leri filtrele
                valid_releases = [r for r in releases if not r.get("draft", False)][:limit]
                
                reports = []
                for release in valid_releases:
                    # .xlsx uzantılı asset'i bul
                    assets = release.get("assets", [])
                    excel_asset = next((a for a in assets if a["name"].endswith(".xlsx")), None)
                    
                    if excel_asset:
                        reports.append({
                            "tag": release.get("tag_name"),
                            "published_at": release.get("published_at"),
                            "download_url": excel_asset["browser_download_url"],
                            "filename": excel_asset["name"]
                        })
                
                logger.info(f"✅ GitHub'dan {len(reports)} rapor linki alındı.")
                return reports
                
        except Exception as e:
            logger.error(f"❌ GitHub releases çekilirken hata: {e}")
            return []

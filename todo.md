# Trendyol Admin Dashboard - TODO

## Backend & Database
- [x] Veritabanı şemasını tasarla (Settings, ScanHistory, GitHubCredentials)
- [x] GitHub API entegrasyonunu kur (Octokit client)
- [x] Workflow tetikleme servisi yaz
- [x] Artifact indirme servisi yaz
- [x] Settings yönetimi tRPC prosedürü yaz
- [x] Scan history tRPC prosedürü yaz
- [x] GitHub workflow status sorgulama prosedürü yaz

## Frontend - Dashboard UI
- [x] DashboardLayout'u özelleştir
- [x] Settings sayfası (Trendyol URL, Telegram Token, Chat ID, Cron expression)
- [x] Workflow Control sayfası (Manuel tetikleme, Durum gösterimi)
- [x] Scan History sayfası (Geçmiş taramalar, başarı/hata durumu)
- [x] Reports sayfası (Excel raporlarına erişim, indirme)
- [x] Real-time notifications (Toast mesajları)
- [x] Responsive tasarım ve mobil uyumluluk
- [x] Loading states ve error handling

## Security & Testing
- [x] GitHub token'ı güvenle sakla (Secrets)
- [x] API rate limiting ve hata yönetimi
- [x] Vitest ile backend testleri yaz
- [x] Admin role kontrolleri

## Deployment & Documentation
- [x] GitHub Actions workflow'unu güncelle (Secrets entegrasyonu)
- [x] Kurulum rehberi yaz
- [x] Checkpoint oluştur

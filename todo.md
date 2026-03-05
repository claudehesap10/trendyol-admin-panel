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

## GitHub Actions Automation (Phase 2)
- [x] GitHub Actions workflow'u test et (manual trigger)
- [x] Scrapling ile Cloudflare bypass'ı doğrula
- [x] Excel rapor oluşturmayı test et
- [x] GitHub Releases'a rapor yüklemeyi test et
- [x] Email göndermeyi test et
- [x] Telegram bildirimi test et

## Dashboard Enhancements (Phase 3-4)
- [x] Rapor görüntüleme sayfası ekle (GitHub Releases'tan çek)
- [x] Rapor indirme linki ekle
- [x] Arama ve filtreleme özelliği
- [x] Sıralama özelliği
- [x] İstatistikler (Ortalama, Min, Max fiyat)
- [x] Express API endpoint'i (/api/reports/latest)
- [x] Excel parse ve JSON dönüşü
- [x] Türkçe column mapping
- [ ] Scan history'yi database'e kaydet
- [ ] Tarama durum göstergesi ekle
- [ ] Hata log'ları göster

## System Testing & Optimization (Phase 5)
- [ ] Saatlik schedule'ı test et
- [ ] Proxy rotation'ı test et
- [ ] Rate limiting'i test et
- [ ] Error recovery'yi test et
- [ ] Performance optimization

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

## Email ve Telegram Entegrasyonu
- [x] Veritabanı şemasına email ayarlarını ekle
- [x] Settings sayfasına email konfigürasyonu UI'sı ekle
- [x] Birden fazla email ekleme/silme özelliği
- [x] Telegram bağlantı test butonu
- [x] Email bağlantı test butonu
- [ ] Backend email test endpoint'i yaz
- [ ] Telegram ve Email status gösterimi (ScanHistory'ye ekle)

## Fiyat Karşılaştırma Tablosu
- [x] PriceComparison sayfası oluştur
- [x] GitHub Releases'tan rapor çek
- [x] Tablo gösterimi (Ürün, Satıcı, Fiyat, Kupon, Rating)
- [x] Arama ve filtreleme
- [x] Sıralama (Fiyat, Puan, Satıcı)
- [x] İstatistikler (Ortalama, Min, Max fiyat)
- [ ] Excel indirme linki
- [ ] Vercel'e deployment

## GitHub Actions Entegrasyonu
- [ ] Raporu JSON formatında GitHub Releases'a yükle
- [ ] Telegram ve Email status'ü rapor ile birlikte gönder
- [ ] Hata yönetimi ve retry mekanizması

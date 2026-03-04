# Vercel Deployment Rehberi

Bu dokümanda Trendyol Admin Dashboard'u Vercel'e deploy etme adımları anlatılmıştır.

## Ön Koşullar

- Vercel hesabı (https://vercel.com)
- GitHub hesabı ve repository
- Vercel CLI (global olarak yüklü)

## Adım 1: Vercel Projesi Oluştur

### Seçenek A: Web UI (Önerilen)

1. [Vercel Dashboard](https://vercel.com/dashboard) açın
2. **"Add New..."** → **"Project"** tıklayın
3. GitHub repository'nizi seçin: `trendyol-admin-panel`
4. **"Import"** tıklayın

### Seçenek B: CLI

```bash
cd /home/ubuntu/trendyol-admin-panel
vercel --prod
```

## Adım 2: Environment Variables Ayarla

Vercel Dashboard'da proje ayarlarına gidin:

**Settings** → **Environment Variables** → Aşağıdaki değişkenleri ekleyin:

```
DATABASE_URL=your_database_url
JWT_SECRET=your_jwt_secret
VITE_APP_ID=your_app_id
OAUTH_SERVER_URL=https://api.manus.im
VITE_OAUTH_PORTAL_URL=your_oauth_portal_url
OWNER_OPEN_ID=your_owner_open_id
OWNER_NAME=your_owner_name
BUILT_IN_FORGE_API_URL=your_forge_api_url
BUILT_IN_FORGE_API_KEY=your_forge_api_key
VITE_FRONTEND_FORGE_API_URL=your_frontend_forge_api_url
VITE_FRONTEND_FORGE_API_KEY=your_frontend_forge_api_key
VITE_APP_TITLE=Trendyol Analiz Admin Paneli
VITE_APP_LOGO=your_logo_url
VITE_ANALYTICS_ENDPOINT=your_analytics_endpoint
VITE_ANALYTICS_WEBSITE_ID=your_analytics_website_id
```

## Adım 3: GitHub Secrets Ayarla

GitHub repository'nize gidin:

**Settings** → **Secrets and variables** → **Actions** → Aşağıdaki secrets'ları ekleyin:

```
VERCEL_TOKEN=your_vercel_token
VERCEL_ORG_ID=your_vercel_org_id
VERCEL_PROJECT_ID=your_vercel_project_id
DATABASE_URL=your_database_url
JWT_SECRET=your_jwt_secret
... (diğer environment variables)
```

### Vercel Token Nasıl Alınır?

1. [Vercel Settings](https://vercel.com/account/tokens) açın
2. **"Create"** tıklayın
3. Token'ı kopyalayın ve GitHub Secrets'a yapıştırın

### Vercel Org ID ve Project ID Nasıl Alınır?

```bash
vercel projects list
```

Komutu çalıştırıp proje bilgilerini alabilirsiniz.

## Adım 4: Otomatik Deployment Workflow

`.github/workflows/deploy.yml` dosyası zaten yapılandırılmıştır.

Bu workflow:
- ✅ Main branch'e push yapıldığında otomatik çalışır
- ✅ Testleri çalıştırır
- ✅ Build işlemini gerçekleştirir
- ✅ Vercel'e deploy eder
- ✅ PR'lara deployment preview URL'i yorum olarak ekler

## Adım 5: İlk Deployment

```bash
git add .
git commit -m "Add Vercel deployment configuration"
git push origin main
```

GitHub Actions workflow otomatik olarak çalışacak ve Vercel'e deploy edecektir.

## Deployment Durumunu Kontrol Et

### GitHub Actions

Repository → **Actions** → En son workflow'u seçin

### Vercel Dashboard

[Vercel Dashboard](https://vercel.com/dashboard) → Proje → **Deployments**

## Sorun Giderme

### Build Hatası

```bash
# Lokal olarak build'i test et
pnpm run build
```

### Environment Variables Eksik

Vercel Dashboard'da tüm gerekli environment variables'ların ekli olduğunu kontrol edin.

### Database Bağlantı Hatası

`DATABASE_URL` değişkeninin doğru olduğundan emin olun.

## Vercel Deployment URL

Deployment başarılı olduğunda, Vercel otomatik olarak bir URL oluşturacaktır:

```
https://trendyol-admin-panel.vercel.app
```

## Özel Domain Bağlama (Opsiyonel)

1. Vercel Dashboard → Proje → **Settings** → **Domains**
2. Özel domain'inizi ekleyin
3. DNS kayıtlarını güncelleyin

## Rollback (Önceki Versiyona Dön)

Vercel Dashboard → **Deployments** → Önceki deployment'ı seçin → **Promote to Production**

## Kaynaklar

- [Vercel Docs](https://vercel.com/docs)
- [Vercel GitHub Integration](https://vercel.com/docs/git/vercel-for-github)
- [Environment Variables](https://vercel.com/docs/projects/environment-variables)

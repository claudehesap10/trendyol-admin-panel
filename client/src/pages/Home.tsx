import { useAuth } from "@/_core/hooks/useAuth";

export default function Home() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Hoş Geldiniz</h1>
        <p className="text-muted-foreground mt-2">Trendyol Satıcı Analiz Paneline hoş geldiniz</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="border rounded-lg p-6 hover:bg-muted/50 transition-colors cursor-pointer">
          <h3 className="font-semibold mb-2">⚙️ Ayarlar</h3>
          <p className="text-sm text-muted-foreground">Trendyol, Telegram ve GitHub ayarlarınızı yapılandırın</p>
        </div>
        <div className="border rounded-lg p-6 hover:bg-muted/50 transition-colors cursor-pointer">
          <h3 className="font-semibold mb-2">▶️ Workflow Kontrolü</h3>
          <p className="text-sm text-muted-foreground">Taramayı manuel olarak başlatın ve durumunu izleyin</p>
        </div>
        <div className="border rounded-lg p-6 hover:bg-muted/50 transition-colors cursor-pointer">
          <h3 className="font-semibold mb-2">📊 Tarama Geçmişi</h3>
          <p className="text-sm text-muted-foreground">Geçmiş tarama işlemlerini ve raporlarını görüntüleyin</p>
        </div>
      </div>

      <div className="border rounded-lg p-6 bg-blue-50">
        <h2 className="font-semibold text-blue-900 mb-2">Başlamak İçin</h2>
        <ol className="list-decimal list-inside space-y-2 text-sm text-blue-800">
          <li>Ayarlar sayfasından Trendyol mağaza URL'sini girin</li>
          <li>Telegram bot token ve chat ID'sini ekleyin</li>
          <li>GitHub token ve repository bilgilerini yapılandırın</li>
          <li>Workflow Kontrolü sayfasından taramayı başlatın</li>
        </ol>
      </div>
    </div>
  );
}

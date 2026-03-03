import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { trpc } from "@/lib/trpc";
import { Loader2, Save } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

export default function Settings() {
  const { user } = useAuth();
  const [isLoading, setIsLoading] = useState(false);

  const { data: settings, isLoading: isLoadingSettings } = trpc.trendyol.settings.get.useQuery();
  const updateSettingsMutation = trpc.trendyol.settings.update.useMutation();

  const [formData, setFormData] = useState({
    trendyolUrl: settings?.trendyolUrl || "",
    telegramToken: settings?.telegramToken || "",
    telegramChatId: settings?.telegramChatId || "",
    cronExpression: settings?.cronExpression || "0 * * * *",
    githubToken: settings?.githubToken || "",
    githubRepo: settings?.githubRepo || "",
    githubWorkflowId: settings?.githubWorkflowId || "",
  });

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await updateSettingsMutation.mutateAsync(formData);
      toast.success("Ayarlar başarıyla kaydedildi!");
    } catch (error) {
      toast.error("Ayarlar kaydedilirken hata oluştu");
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoadingSettings) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Ayarlar</h1>
        <p className="text-muted-foreground mt-2">Trendyol analiz otomasyonunuz için ayarları yapılandırın</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Trendyol Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Trendyol Mağazası</CardTitle>
            <CardDescription>Analiz edilecek mağaza bilgileri</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="trendyolUrl">Mağaza URL'si</Label>
              <Input
                id="trendyolUrl"
                name="trendyolUrl"
                value={formData.trendyolUrl}
                onChange={handleInputChange}
                placeholder="https://www.trendyol.com/sr?mid=..."
                className="mt-2"
              />
            </div>
          </CardContent>
        </Card>

        {/* Telegram Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Telegram Bilgileri</CardTitle>
            <CardDescription>Raporları almak için Telegram bot ayarları</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="telegramToken">Bot Token</Label>
              <Input
                id="telegramToken"
                name="telegramToken"
                type="password"
                value={formData.telegramToken}
                onChange={handleInputChange}
                placeholder="123456:ABC-DEF..."
                className="mt-2"
              />
            </div>
            <div>
              <Label htmlFor="telegramChatId">Chat ID</Label>
              <Input
                id="telegramChatId"
                name="telegramChatId"
                value={formData.telegramChatId}
                onChange={handleInputChange}
                placeholder="987654321"
                className="mt-2"
              />
            </div>
          </CardContent>
        </Card>

        {/* GitHub Settings */}
        <Card>
          <CardHeader>
            <CardTitle>GitHub Entegrasyonu</CardTitle>
            <CardDescription>GitHub Actions workflow'larını yönetmek için gerekli bilgiler</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="githubToken">GitHub Token (Personal Access Token)</Label>
              <Input
                id="githubToken"
                name="githubToken"
                type="password"
                value={formData.githubToken}
                onChange={handleInputChange}
                placeholder="ghp_..."
                className="mt-2"
              />
              <p className="text-xs text-muted-foreground mt-2">
                Token'ı <a href="https://github.com/settings/tokens" target="_blank" rel="noopener noreferrer" className="underline">GitHub Settings</a>'ten oluşturun
              </p>
            </div>
            <div>
              <Label htmlFor="githubRepo">Repository (owner/repo)</Label>
              <Input
                id="githubRepo"
                name="githubRepo"
                value={formData.githubRepo}
                onChange={handleInputChange}
                placeholder="username/trendyol-project"
                className="mt-2"
              />
            </div>
            <div>
              <Label htmlFor="githubWorkflowId">Workflow ID</Label>
              <Input
                id="githubWorkflowId"
                name="githubWorkflowId"
                value={formData.githubWorkflowId}
                onChange={handleInputChange}
                placeholder="hourly_scan.yml"
                className="mt-2"
              />
            </div>
          </CardContent>
        </Card>

        {/* Cron Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Tarama Sıklığı</CardTitle>
            <CardDescription>GitHub Actions workflow'unun çalışma sıklığını belirleyin (Cron expression)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="cronExpression">Cron Expression</Label>
              <Textarea
                id="cronExpression"
                name="cronExpression"
                value={formData.cronExpression}
                onChange={handleInputChange}
                placeholder="0 * * * * (Her saat başı)"
                className="mt-2 font-mono"
                rows={3}
              />
              <p className="text-xs text-muted-foreground mt-2">
                Cron expression formatı: <code>dakika saat gün ay haftanın günü</code>
              </p>
              <ul className="text-xs text-muted-foreground mt-2 list-disc list-inside">
                <li><code>0 * * * *</code> - Her saat başı</li>
                <li><code>0 0 * * *</code> - Her gün saat 00:00'da</li>
                <li><code>0 */6 * * *</code> - Her 6 saatte bir</li>
              </ul>
            </div>
          </CardContent>
        </Card>

        <Button type="submit" disabled={isLoading} className="w-full">
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Kaydediliyor...
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              Ayarları Kaydet
            </>
          )}
        </Button>
      </form>
    </div>
  );
}

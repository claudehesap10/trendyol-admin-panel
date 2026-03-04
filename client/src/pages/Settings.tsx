import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { trpc } from "@/lib/trpc";
import { Loader2, Save, Plus, Trash2, CheckCircle2, AlertCircle, Clock } from "lucide-react";
import { useState, useEffect } from "react";
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
    smtpServer: settings?.smtpServer || "smtp.gmail.com",
    smtpPort: settings?.smtpPort || "587",
    smtpEmail: settings?.smtpEmail || "",
    smtpPassword: settings?.smtpPassword || "",
    recipientEmails: settings?.recipientEmails?.split(",").map(e => e.trim()) || [],
    cronExpression: settings?.cronExpression || "0 * * * *",
    githubToken: settings?.githubToken || "",
    githubRepo: settings?.githubRepo || "",
    githubWorkflowId: settings?.githubWorkflowId || "",
  });
  const [newEmail, setNewEmail] = useState("");
  const [telegramStatus, setTelegramStatus] = useState<"success" | "error" | "pending" | null>(null);
  const [emailStatus, setEmailStatus] = useState<"success" | "error" | "pending" | null>(null);
  const [lastTelegramCheck, setLastTelegramCheck] = useState<Date | null>(null);
  const [lastEmailCheck, setLastEmailCheck] = useState<Date | null>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleAddEmail = () => {
    if (!newEmail.trim()) {
      toast.error("Lütfen bir email adresi girin");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(newEmail)) {
      toast.error("Geçerli bir email adresi girin");
      return;
    }
    if (formData.recipientEmails.includes(newEmail)) {
      toast.error("Bu email zaten eklenmiş");
      return;
    }
    setFormData((prev) => ({
      ...prev,
      recipientEmails: [...prev.recipientEmails, newEmail],
    }));
    setNewEmail("");
    toast.success("Email eklendi");
  };

  const handleRemoveEmail = (email: string) => {
    setFormData((prev) => ({
      ...prev,
      recipientEmails: prev.recipientEmails.filter((e) => e !== email),
    }));
    toast.success("Email kaldırıldı");
  };

  const testTelegramConnection = async () => {
    if (!formData.telegramToken || !formData.telegramChatId) {
      toast.error("Telegram token ve chat ID'sini girin");
      return;
    }
    setTelegramStatus("pending");
    try {
      const response = await fetch(`https://api.telegram.org/bot${formData.telegramToken}/sendMessage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: formData.telegramChatId,
          text: "✅ Trendyol Admin Panel - Telegram bağlantısı başarılı!",
        }),
      });
      if (response.ok) {
        setTelegramStatus("success");
        setLastTelegramCheck(new Date());
        toast.success("Telegram bağlantısı başarılı!");
      } else {
        setTelegramStatus("error");
        toast.error("Telegram bağlantısı başarısız");
      }
    } catch (error) {
      setTelegramStatus("error");
      toast.error("Telegram bağlantısı test edilemedi");
    }
  };

  const testEmailConnection = async () => {
    if (!formData.smtpEmail || !formData.smtpPassword || formData.recipientEmails.length === 0) {
      toast.error("Email ayarlarını tamamlayın");
      return;
    }
    setEmailStatus("pending");
    try {
      // Backend'e test isteği gönder
      const response = await fetch("/api/test-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          smtpServer: formData.smtpServer,
          smtpPort: parseInt(formData.smtpPort),
          smtpEmail: formData.smtpEmail,
          smtpPassword: formData.smtpPassword,
          recipientEmail: formData.recipientEmails[0],
        }),
      });
      if (response.ok) {
        setEmailStatus("success");
        setLastEmailCheck(new Date());
        toast.success("Email bağlantısı başarılı!");
      } else {
        setEmailStatus("error");
        toast.error("Email bağlantısı başarısız");
      }
    } catch (error) {
      setEmailStatus("error");
      toast.error("Email bağlantısı test edilemedi");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await updateSettingsMutation.mutateAsync({
        ...formData,
        recipientEmails: formData.recipientEmails.join(","),
      });
      toast.success("Ayarlar başarıyla kaydedildi!");
    } catch (error) {
      toast.error("Ayarlar kaydedilirken hata oluştu");
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (settings) {
      setFormData({
        trendyolUrl: settings.trendyolUrl || "",
        telegramToken: settings.telegramToken || "",
        telegramChatId: settings.telegramChatId || "",
        smtpServer: settings.smtpServer || "smtp.gmail.com",
        smtpPort: settings.smtpPort || "587",
        smtpEmail: settings.smtpEmail || "",
        smtpPassword: settings.smtpPassword || "",
        recipientEmails: settings.recipientEmails?.split(",").map(e => e.trim()) || [],
        cronExpression: settings.cronExpression || "0 * * * *",
        githubToken: settings.githubToken || "",
        githubRepo: settings.githubRepo || "",
        githubWorkflowId: settings.githubWorkflowId || "",
      });
    }
  }, [settings]);

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
            <div className="flex items-center justify-between mb-4 p-3 bg-muted rounded-lg">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">Telegram Durumu:</span>
                {telegramStatus === "success" && (
                  <div className="flex items-center gap-1">
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    <span className="text-xs text-green-600">Bağlı</span>
                  </div>
                )}
                {telegramStatus === "error" && (
                  <div className="flex items-center gap-1">
                    <AlertCircle className="h-4 w-4 text-red-600" />
                    <span className="text-xs text-red-600">Bağlantı Başarısız</span>
                  </div>
                )}
                {telegramStatus === "pending" && (
                  <div className="flex items-center gap-1">
                    <Clock className="h-4 w-4 text-blue-600 animate-spin" />
                    <span className="text-xs text-blue-600">Test Ediliyor...</span>
                  </div>
                )}
                {!telegramStatus && (
                  <span className="text-xs text-muted-foreground">Test edilmedi</span>
                )}
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={testTelegramConnection}
                disabled={!formData.telegramToken || !formData.telegramChatId}
              >
                Test Et
              </Button>
            </div>
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

        {/* Email Settings */}
        <Card>
          <CardHeader>
            <CardTitle>Email Ayarları</CardTitle>
            <CardDescription>SMTP ayarları ve alıcı email adreslerini yapılandırın</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between mb-4 p-3 bg-muted rounded-lg">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">Email Durumu:</span>
                {emailStatus === "success" && (
                  <div className="flex items-center gap-1">
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    <span className="text-xs text-green-600">Bağlı</span>
                  </div>
                )}
                {emailStatus === "error" && (
                  <div className="flex items-center gap-1">
                    <AlertCircle className="h-4 w-4 text-red-600" />
                    <span className="text-xs text-red-600">Bağlantı Başarısız</span>
                  </div>
                )}
                {emailStatus === "pending" && (
                  <div className="flex items-center gap-1">
                    <Clock className="h-4 w-4 text-blue-600 animate-spin" />
                    <span className="text-xs text-blue-600">Test Ediliyor...</span>
                  </div>
                )}
                {!emailStatus && (
                  <span className="text-xs text-muted-foreground">Test edilmedi</span>
                )}
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={testEmailConnection}
                disabled={!formData.smtpEmail || !formData.smtpPassword || formData.recipientEmails.length === 0}
              >
                Test Et
              </Button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="smtpServer">SMTP Sunucusu</Label>
                <Input
                  id="smtpServer"
                  name="smtpServer"
                  value={formData.smtpServer}
                  onChange={handleInputChange}
                  placeholder="smtp.gmail.com"
                  className="mt-2"
                />
              </div>
              <div>
                <Label htmlFor="smtpPort">SMTP Port</Label>
                <Input
                  id="smtpPort"
                  name="smtpPort"
                  value={formData.smtpPort}
                  onChange={handleInputChange}
                  placeholder="587"
                  className="mt-2"
                />
              </div>
            </div>
            <div>
              <Label htmlFor="smtpEmail">Email Adresi</Label>
              <Input
                id="smtpEmail"
                name="smtpEmail"
                type="email"
                value={formData.smtpEmail}
                onChange={handleInputChange}
                placeholder="your-email@gmail.com"
                className="mt-2"
              />
            </div>
            <div>
              <Label htmlFor="smtpPassword">Email Şifresi / App Password</Label>
              <Input
                id="smtpPassword"
                name="smtpPassword"
                type="password"
                value={formData.smtpPassword}
                onChange={handleInputChange}
                placeholder="••••••••••••••••"
                className="mt-2"
              />
              <p className="text-xs text-muted-foreground mt-2">
                Gmail kullanıyorsanız, <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" className="underline">App Password</a> oluşturun
              </p>
            </div>
            <div>
              <Label htmlFor="newEmail">Alıcı Email Adreslerini Ekle</Label>
              <div className="flex gap-2 mt-2">
                <Input
                  id="newEmail"
                  type="email"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="alıcı@example.com"
                  onKeyPress={(e) => e.key === "Enter" && handleAddEmail()}
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleAddEmail}
                  size="sm"
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            </div>
            {formData.recipientEmails.length > 0 && (
              <div>
                <Label>Ekli Email Adresleri</Label>
                <div className="flex flex-wrap gap-2 mt-2">
                  {formData.recipientEmails.map((email) => (
                    <Badge key={email} variant="secondary" className="flex items-center gap-2">
                      {email}
                      <button
                        type="button"
                        onClick={() => handleRemoveEmail(email)}
                        className="ml-1 hover:text-red-600"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              </div>
            )}
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

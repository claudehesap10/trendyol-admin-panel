import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { trpc } from "@/lib/trpc";
import { Loader2, Play, RefreshCw } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

export default function WorkflowControl() {
  const { user } = useAuth();
  const [isTriggering, setIsTriggering] = useState(false);

  const { data: settings, isLoading: isLoadingSettings } = trpc.trendyol.settings.get.useQuery();
  const { data: workflows, isLoading: isLoadingWorkflows, refetch } = trpc.trendyol.workflows.list.useQuery(
    settings?.githubRepo && settings?.githubWorkflowId
      ? {
          owner: settings.githubRepo.split("/")[0],
          repo: settings.githubRepo.split("/")[1],
          workflowId: settings.githubWorkflowId,
        }
      : { owner: "", repo: "", workflowId: "" },
    { enabled: !!settings?.githubRepo && !!settings?.githubWorkflowId }
  );

  const triggerWorkflowMutation = trpc.trendyol.workflows.trigger.useMutation();

  const handleTriggerWorkflow = async () => {
    if (!settings?.githubRepo || !settings?.githubWorkflowId) {
      toast.error("GitHub ayarlarını tamamlayın");
      return;
    }

    setIsTriggering(true);
    try {
      const [owner, repo] = settings.githubRepo.split("/");
      await triggerWorkflowMutation.mutateAsync({
        owner,
        repo,
        workflowId: settings.githubWorkflowId,
      });
      toast.success("Workflow başarıyla tetiklendi!");
      setTimeout(() => refetch(), 2000);
    } catch (error) {
      toast.error("Workflow tetiklenirken hata oluştu");
      console.error(error);
    } finally {
      setIsTriggering(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-800";
      case "in_progress":
        return "bg-blue-100 text-blue-800";
      case "failed":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "completed":
        return "Tamamlandı";
      case "in_progress":
        return "Çalışıyor";
      case "failed":
        return "Başarısız";
      case "pending":
        return "Bekleniyor";
      default:
        return status;
    }
  };

  if (isLoadingSettings) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="animate-spin" />
      </div>
    );
  }

  if (!settings?.githubRepo || !settings?.githubWorkflowId) {
    return (
      <Card className="border-yellow-200 bg-yellow-50">
        <CardHeader>
          <CardTitle className="text-yellow-900">GitHub Ayarları Eksik</CardTitle>
          <CardDescription className="text-yellow-800">
            Workflow'u kontrol etmek için önce Settings sayfasından GitHub ayarlarını tamamlayın.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Workflow Kontrolü</h1>
        <p className="text-muted-foreground mt-2">GitHub Actions workflow'unuzu yönetin ve tetikleyin</p>
      </div>

      {/* Trigger Button */}
      <Card>
        <CardHeader>
          <CardTitle>Taramayı Başlat</CardTitle>
          <CardDescription>Trendyol mağazasının taramasını hemen başlatın</CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            onClick={handleTriggerWorkflow}
            disabled={isTriggering}
            size="lg"
            className="w-full"
          >
            {isTriggering ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Tetikleniyor...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Taramayı Başlat
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Recent Runs */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Son Çalıştırmalar</CardTitle>
            <CardDescription>En son 10 workflow çalıştırması</CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isLoadingWorkflows}
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent>
          {isLoadingWorkflows ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="animate-spin" />
            </div>
          ) : workflows && workflows.length > 0 ? (
            <div className="space-y-3">
              {workflows.map((run) => (
                <div key={run.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex-1">
                    <p className="font-medium">{run.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {new Date(run.createdAt).toLocaleString("tr-TR")}
                    </p>
                  </div>
                  <Badge className={getStatusColor(run.status)}>
                    {getStatusLabel(run.status)}
                  </Badge>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-muted-foreground py-8">Henüz workflow çalıştırması yok</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

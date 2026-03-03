import { useAuth } from "@/_core/hooks/useAuth";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { trpc } from "@/lib/trpc";
import { Loader2, Download, AlertCircle, CheckCircle2 } from "lucide-react";

export default function ScanHistory() {
  const { user } = useAuth();
  const { data: history, isLoading } = trpc.trendyol.history.list.useQuery();

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

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case "failed":
        return <AlertCircle className="h-5 w-5 text-red-600" />;
      case "in_progress":
        return <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />;
      default:
        return null;
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Tarama Geçmişi</h1>
        <p className="text-muted-foreground mt-2">Geçmiş tarama işlemlerinin detaylarını görüntüleyin</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Son Taramalar</CardTitle>
          <CardDescription>En son 20 tarama işlemi</CardDescription>
        </CardHeader>
        <CardContent>
          {history && history.length > 0 ? (
            <div className="space-y-3">
              {history.map((scan) => (
                <div key={scan.id} className="border rounded-lg p-4 hover:bg-muted/50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3 flex-1">
                      <div className="mt-1">{getStatusIcon(scan.status)}</div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium">Workflow Run #{scan.workflowRunId}</h3>
                          <Badge className={getStatusColor(scan.status)}>
                            {getStatusLabel(scan.status)}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          Başlangıç: {new Date(scan.startedAt).toLocaleString("tr-TR")}
                        </p>
                        {scan.completedAt && (
                          <p className="text-sm text-muted-foreground">
                            Bitiş: {new Date(scan.completedAt).toLocaleString("tr-TR")}
                          </p>
                        )}
                        {scan.productCount && (
                          <p className="text-sm text-muted-foreground">
                            Taranılan Ürün: {scan.productCount}
                          </p>
                        )}
                        {scan.errorMessage && (
                          <p className="text-sm text-red-600 mt-2">
                            Hata: {scan.errorMessage}
                          </p>
                        )}
                      </div>
                    </div>
                    {scan.reportUrl && (
                      <a
                        href={scan.reportUrl}
                        download
                        className="ml-4 inline-flex items-center gap-2 px-3 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
                      >
                        <Download className="h-4 w-4" />
                        İndir
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-muted-foreground py-8">Henüz tarama işlemi yok</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

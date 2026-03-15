"use client";
import { useState, useEffect } from "react";
import { useLocation } from "wouter";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, TrendingUp, TrendingDown, Minus, ExternalLink, RefreshCw, Layers } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

interface ChangeItem {
  product: string;
  barcode: string;
  url: string;
  seller: string;
  new_price: number;
  old_price: number | null;
  diff: number;
  percent: number;
  status: "Zam" | "İndirim" | "Sabit" | "Yeni Satıcı";
}

interface Summary {
  new_report: { tag: string; date: string };
  old_report: { tag: string; date: string };
  stats: {
    "İndirim": number;
    "Zam": number;
    "Sabit": number;
    "Yeni Satıcı": number;
    "Total": number;
  };
}

export default function Analysis() {
  const [, setLocation] = useLocation();
  const [changes, setChanges] = useState<ChangeItem[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/reports/compare?show_all=false");
      if (!response.ok) throw new Error("Veri yüklenemedi");
      const result = await response.json();
      if (result.success) {
        setChanges(result.data.changes);
        setSummary(result.data.summary);
      } else {
        setError(result.message || "Bir hata oluştu");
      }
    } catch (err) {
      setError("Bağlantı hatası oluştu.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="p-8 max-w-7xl mx-auto space-y-6">
        <Skeleton className="h-12 w-64" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-24 w-full" />)}
        </div>
        <Skeleton className="h-[500px] w-full" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f9fafb] p-4 md:p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <Button 
              variant="ghost" 
              size="icon" 
              onClick={() => setLocation("/reports")}
              className="rounded-full hover:bg-white shadow-sm border border-zinc-200"
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-3xl font-black text-zinc-900 tracking-tight">Fiyat Karşılaştırma</h1>
              {summary && (
                <p className="text-sm text-zinc-500 font-medium">
                  {summary.old_report.tag} → {summary.new_report.tag}
                </p>
              )}
            </div>
          </div>
          <Button onClick={fetchData} variant="outline" className="bg-white rounded-xl shadow-sm border-zinc-200">
            <RefreshCw className="mr-2 h-4 w-4" /> Yenile
          </Button>
        </div>

        {error ? (
          <Card className="border-red-100 bg-red-50">
            <CardContent className="py-12 text-center">
              <p className="text-red-600 font-semibold">{error}</p>
              <Button onClick={() => setLocation("/reports")} variant="link" className="text-red-500 mt-2">
                Raporlar sayfasında tarama başlatabilirsiniz.
              </Button>
            </CardContent>
          </Card>
        ) : (
          <>
            {/* Stats Overview */}
            {summary && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-white p-6 rounded-3xl border border-zinc-200 shadow-sm flex flex-col items-center">
                  <div className="text-3xl font-black text-emerald-600">{summary.stats.İndirim}</div>
                  <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mt-1">İndirimler</div>
                </div>
                <div className="bg-white p-6 rounded-3xl border border-zinc-200 shadow-sm flex flex-col items-center">
                  <div className="text-3xl font-black text-amber-600">{summary.stats.Zam}</div>
                  <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mt-1">Zamlar</div>
                </div>
                <div className="bg-white p-6 rounded-3xl border border-zinc-200 shadow-sm flex flex-col items-center">
                  <div className="text-3xl font-black text-blue-600">{summary.stats["Yeni Satıcı"]}</div>
                  <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mt-1">Yeni Satıcı</div>
                </div>
                <div className="bg-white p-6 rounded-3xl border border-zinc-200 shadow-sm flex flex-col items-center">
                  <div className="text-3xl font-black text-zinc-400">{summary.stats.Sabit}</div>
                  <div className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mt-1">Değişmeyen</div>
                </div>
              </div>
            )}

            {/* List Table */}
            <Card className="rounded-3xl border-zinc-200 shadow-sm overflow-hidden bg-white">
              <CardHeader className="border-b bg-zinc-50/50 px-6 py-4">
                <div className="flex items-center gap-2">
                  <Layers className="h-4 w-4 text-zinc-400" />
                  <CardTitle className="text-sm font-bold text-zinc-600 uppercase tracking-wider">Değişim Listesi</CardTitle>
                </div>
              </CardHeader>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader className="bg-zinc-50">
                    <TableRow>
                      <TableHead className="font-bold text-zinc-900">Ürün Adı</TableHead>
                      <TableHead className="font-bold text-zinc-900">Barkod</TableHead>
                      <TableHead className="font-bold text-zinc-900">Satıcı</TableHead>
                      <TableHead className="text-right font-bold text-zinc-900">Eski Fiyat</TableHead>
                      <TableHead className="text-right font-bold text-zinc-900">Yeni Fiyat</TableHead>
                      <TableHead className="text-right font-bold text-zinc-900">Değişim</TableHead>
                      <TableHead className="text-center font-bold text-zinc-900">Durum</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {changes.map((item, idx) => (
                      <TableRow key={idx} className="hover:bg-zinc-50/50 transition-colors">
                        <TableCell className="max-w-[300px]">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-zinc-900 truncate" title={item.product}>{item.product}</span>
                            <a href={item.url} target="_blank" rel="noreferrer" className="text-zinc-400 hover:text-zinc-900 shrink-0">
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          </div>
                        </TableCell>
                        <TableCell className="text-[11px] font-mono text-zinc-500 whitespace-nowrap">
                          {item.barcode || "-"}
                        </TableCell>
                        <TableCell className="text-zinc-600 font-medium">{item.seller}</TableCell>
                        <TableCell className="text-right text-zinc-400 font-medium">
                          {item.old_price ? `₺${item.old_price.toFixed(2)}` : "-"}
                        </TableCell>
                        <TableCell className="text-right font-black text-zinc-900">
                          ₺{item.new_price.toFixed(2)}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className={`flex flex-col items-end ${item.diff > 0 ? "text-red-600" : item.diff < 0 ? "text-emerald-600" : "text-zinc-400"}`}>
                            <span className="font-bold">
                              {item.diff > 0 ? "+" : ""}{item.diff.toFixed(2)} ₺
                            </span>
                            <span className="text-[10px] font-medium opacity-80">
                              {item.percent > 0 ? "+" : ""}{item.percent}%
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge className={`
                            ${item.status === "İndirim" ? "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100" : 
                              item.status === "Zam" ? "bg-red-50 text-red-700 border-red-200 hover:bg-red-100" :
                              item.status === "Yeni Satıcı" ? "bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100" :
                              "bg-zinc-50 text-zinc-500 border-zinc-200 hover:bg-zinc-100"}
                            border shadow-none rounded-lg text-[10px] font-bold h-6 uppercase tracking-wider
                          `}>
                            {item.status}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}

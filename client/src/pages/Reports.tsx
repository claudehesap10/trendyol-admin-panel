import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2, Download, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import * as XLSX from "xlsx";

interface ReportData {
  [key: string]: any;
  "Ürün Adı"?: string;
  "Satıcı Adı"?: string;
  "Fiyat"?: number;
  "Rating"?: number;
  // Fallback to English names
  productName?: string;
  seller?: string;
  price?: number;
  rating?: number;
  reviews?: number;
  coupon?: string;
  stock?: string;
}

export default function Reports() {
  const [reports, setReports] = useState<any[]>([]);
  const [tableData, setTableData] = useState<ReportData[]>([]);
  const [filteredData, setFilteredData] = useState<ReportData[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: "asc" | "desc" } | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Backend'den raporları çek
  const fetchReports = async () => {
    setIsLoading(true);
    try {
      const response = await fetch("/api/reports/latest");
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const reportData = await response.json();
      
      if (reportData?.data && Array.isArray(reportData.data)) {
        const data = reportData.data as ReportData[];
        setTableData(data);
        setFilteredData(data);
        setReports(reportData.releases || []);
        toast.success(`Rapor başarıyla yüklendi! (${data.length} ürün)`);
      } else {
        toast.warning("Rapor verisi bulunamadı");
      }
    } catch (error) {
      console.error("Error fetching reports:", error);
      toast.error(`Rapor yüklenirken hata oluştu: ${error instanceof Error ? error.message : "Bilinmeyen hata"}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  // Arama filtresi
  const handleSearch = (value: string) => {
    setSearchTerm(value);
    const filtered = tableData.filter((item) => {
      const productName = item["Ürün Adı"] || item.productName || "";
      const seller = item["Satıcı Adı"] || item.seller || "";
      return (
        String(productName).toLowerCase().includes(value.toLowerCase()) ||
        String(seller).toLowerCase().includes(value.toLowerCase())
      );
    });
    setFilteredData(filtered);
  };

  // Sıralama
  const handleSort = (key: string) => {
    let direction: "asc" | "desc" = "asc";
    if (sortConfig?.key === key && sortConfig.direction === "asc") {
      direction = "desc";
    }
    setSortConfig({ key, direction });

    const sorted = [...filteredData].sort((a, b) => {
      const aVal = a[key];
      const bVal = b[key];

      if (typeof aVal === "number" && typeof bVal === "number") {
        return direction === "asc" ? aVal - bVal : bVal - aVal;
      }

      if (typeof aVal === "string" && typeof bVal === "string") {
        return direction === "asc"
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }

      return 0;
    });

    setFilteredData(sorted);
  };

  // Excel'e indir
  const downloadExcel = () => {
    if (filteredData.length === 0) {
      toast.error("İndirilecek veri yok");
      return;
    }

    const worksheet = XLSX.utils.json_to_sheet(filteredData);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Raporlar");
    XLSX.writeFile(workbook, `trendyol_rapor_${new Date().toISOString().split("T")[0]}.xlsx`);
    toast.success("Rapor başarıyla indirildi!");
  };

  return (
    <div className="space-y-6 p-4">
      <div>
        <h1 className="text-3xl font-bold">Fiyat Karşılaştırma Raporları</h1>
        <p className="text-muted-foreground mt-2">
          GitHub Releases'tan en son raporları görüntüleyin ve analiz edin
        </p>
      </div>

      {/* Kontrol Paneli */}
      <Card>
        <CardHeader>
          <CardTitle>Rapor Kontrolleri</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="Ürün adı veya satıcı ara..."
              value={searchTerm}
              onChange={(e) => handleSearch(e.target.value)}
              className="flex-1"
            />
            <Button onClick={fetchReports} disabled={isLoading} variant="outline">
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
            </Button>
            <Button onClick={downloadExcel} disabled={filteredData.length === 0}>
              <Download className="h-4 w-4 mr-2" />
              İndir
            </Button>
          </div>

          {/* İstatistikler */}
          {filteredData.length > 0 && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-muted p-3 rounded-lg">
                <p className="text-sm text-muted-foreground">Toplam Ürün</p>
                <p className="text-2xl font-bold">{filteredData.length}</p>
              </div>
              {filteredData.some(item => typeof item.price === 'number') && (
                <>
                  <div className="bg-muted p-3 rounded-lg">
                    <p className="text-sm text-muted-foreground">Ortalama Fiyat</p>
                    <p className="text-2xl font-bold">
                      ₺{(filteredData.reduce((sum, item) => sum + (typeof item.price === 'number' ? item.price : 0), 0) / filteredData.length).toFixed(2)}
                    </p>
                  </div>
                  <div className="bg-muted p-3 rounded-lg">
                    <p className="text-sm text-muted-foreground">Min Fiyat</p>
                    <p className="text-2xl font-bold">
                      ₺{Math.min(...(filteredData.filter(item => typeof item.price === 'number').map((item) => item.price as number) || [Infinity])).toFixed(2)}
                    </p>
                  </div>
                  <div className="bg-muted p-3 rounded-lg">
                    <p className="text-sm text-muted-foreground">Max Fiyat</p>
                    <p className="text-2xl font-bold">
                      ₺{Math.max(...(filteredData.filter(item => typeof item.price === 'number').map((item) => item.price as number) || [-Infinity])).toFixed(2)}
                    </p>
                  </div>
                </>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tablo */}
      <Card>
        <CardHeader>
          <CardTitle>Ürün Listesi</CardTitle>
          <CardDescription>
            {filteredData.length} ürün gösteriliyor
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center h-96">
              <Loader2 className="animate-spin h-8 w-8" />
            </div>
          ) : filteredData.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">Henüz rapor yok</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th
                      className="text-left py-3 px-4 font-semibold cursor-pointer hover:bg-muted"
                      onClick={() => handleSort("productName")}
                    >
                      Ürün Adı {sortConfig?.key === "productName" && (sortConfig.direction === "asc" ? "↑" : "↓")}
                    </th>
                    <th
                      className="text-left py-3 px-4 font-semibold cursor-pointer hover:bg-muted"
                      onClick={() => handleSort("seller")}
                    >
                      Satıcı {sortConfig?.key === "seller" && (sortConfig.direction === "asc" ? "↑" : "↓")}
                    </th>
                    <th
                      className="text-right py-3 px-4 font-semibold cursor-pointer hover:bg-muted"
                      onClick={() => handleSort("price")}
                    >
                      Fiyat {sortConfig?.key === "price" && (sortConfig.direction === "asc" ? "↑" : "↓")}
                    </th>
                    <th
                      className="text-right py-3 px-4 font-semibold cursor-pointer hover:bg-muted"
                      onClick={() => handleSort("rating")}
                    >
                      Puan {sortConfig?.key === "rating" && (sortConfig.direction === "asc" ? "↑" : "↓")}
                    </th>
                    <th className="text-right py-3 px-4 font-semibold">İncelemeler</th>
                    <th className="text-left py-3 px-4 font-semibold">Kupon</th>
                    <th className="text-left py-3 px-4 font-semibold">Stok</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredData.map((item, index) => {
                    const productName = item["Ürün Adı"] || item.productName || "N/A";
                    const seller = item["Satıcı Adı"] || item.seller || "N/A";
                    const price = item["Fiyat"] || item.price || 0;
                    const rating = item["Rating"] || item.rating || 0;
                    const reviews = item.reviews || 0;
                    const priceNum = typeof price === 'number' ? price : parseFloat(String(price)) || 0;
                    const ratingNum = typeof rating === 'number' ? rating : parseFloat(String(rating)) || 0;
                    
                    return (
                    <tr key={index} className="border-b hover:bg-muted/50">
                      <td className="py-3 px-4">{productName}</td>
                      <td className="py-3 px-4">{seller}</td>
                      <td className="text-right py-3 px-4 font-semibold">₺{priceNum.toFixed(2)}</td>
                      <td className="text-right py-3 px-4">
                        <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs font-semibold">
                          {ratingNum.toFixed(1)} ⭐
                        </span>
                      </td>
                      <td className="text-right py-3 px-4 text-muted-foreground">{reviews}</td>
                      <td className="py-3 px-4">
                        {item.coupon ? (
                          <span className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs font-semibold">
                            {item.coupon}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-1 rounded text-xs font-semibold ${
                            item.stock === "Stokta" || item.stock === "In Stock"
                              ? "bg-green-100 text-green-800"
                              : "bg-red-100 text-red-800"
                          }`}
                        >
                          {item.stock}
                        </span>
                      </td>
                    </tr>
                  );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Son Releases */}
      {reports.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Rapor Geçmişi</CardTitle>
            <CardDescription>Son 10 rapor</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {reports.slice(0, 10).map((release) => (
                <div
                  key={release.id}
                  className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50"
                >
                  <div>
                    <p className="font-semibold">{release.tag_name}</p>
                    <p className="text-sm text-muted-foreground">
                      {new Date(release.created_at).toLocaleString("tr-TR")}
                    </p>
                  </div>
                  {release.assets && release.assets.length > 0 && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={fetchReports}
                    >
                      Yükle
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

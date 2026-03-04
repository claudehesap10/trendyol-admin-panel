import { useAuth } from "@/_core/hooks/useAuth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { trpc } from "@/lib/trpc";
import { Loader2, Download, RefreshCw, TrendingDown, TrendingUp } from "lucide-react";
import { useState, useEffect } from "react";
import { toast } from "sonner";

interface ProductData {
  productName: string;
  productLink: string;
  seller: string;
  originalPrice: number;
  coupon: string;
  cartDiscount: string;
  finalPrice: number;
  rating: number;
  notes: string;
}

export default function PriceComparison() {
  const { user } = useAuth();
  const [products, setProducts] = useState<ProductData[]>([]);
  const [filteredProducts, setFilteredProducts] = useState<ProductData[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState<"price" | "rating" | "seller">("price");

  const { data: settings } = trpc.trendyol.settings.get.useQuery();
  const { data: history } = trpc.trendyol.history.list.useQuery();

  useEffect(() => {
    // En son raporu GitHub Releases'tan çek
    const fetchLatestReport = async () => {
      if (!settings?.githubRepo || !settings?.githubToken) {
        toast.error("GitHub ayarlarını yapılandırın");
        return;
      }

      setIsLoading(true);
      try {
        const [owner, repo] = settings.githubRepo.split("/");
        // GitHub Releases API'sinden en son raporu çek
        const response = await fetch(
          `https://api.github.com/repos/${owner}/${repo}/releases/latest`,
          {
            headers: {
              Authorization: `token ${settings.githubToken}`,
              Accept: "application/vnd.github.v3+json",
            },
          }
        );

        if (!response.ok) {
          toast.error("Rapor alınamadı");
          return;
        }

        const release = await response.json();
        
        // Excel dosyasını indir ve parse et
        const excelAsset = release.assets.find((a: any) => a.name.endsWith(".xlsx"));
        if (!excelAsset) {
          toast.error("Excel raporu bulunamadı");
          return;
        }

        // Basit JSON formatında rapor varsa onu kullan
        const jsonAsset = release.assets.find((a: any) => a.name.endsWith(".json"));
        if (jsonAsset) {
          const jsonResponse = await fetch(jsonAsset.browser_download_url);
          const data = await jsonResponse.json();
          setProducts(data);
          filterAndSort(data, searchTerm, sortBy);
        } else {
          toast.info("Rapor henüz hazır değil, lütfen biraz sonra tekrar deneyin");
        }
      } catch (error) {
        console.error("Error fetching report:", error);
        toast.error("Rapor alınırken hata oluştu");
      } finally {
        setIsLoading(false);
      }
    };

    if (settings?.githubRepo) {
      fetchLatestReport();
    }
  }, [settings?.githubRepo, settings?.githubToken]);

  const filterAndSort = (data: ProductData[], search: string, sort: string) => {
    let filtered = data;

    if (search) {
      filtered = data.filter(
        (p) =>
          p.productName.toLowerCase().includes(search.toLowerCase()) ||
          p.seller.toLowerCase().includes(search.toLowerCase())
      );
    }

    const sorted = [...filtered].sort((a, b) => {
      switch (sort) {
        case "price":
          return a.finalPrice - b.finalPrice;
        case "rating":
          return b.rating - a.rating;
        case "seller":
          return a.seller.localeCompare(b.seller);
        default:
          return 0;
      }
    });

    setFilteredProducts(sorted);
  };

  const handleSearch = (value: string) => {
    setSearchTerm(value);
    filterAndSort(products, value, sortBy);
  };

  const handleSort = (value: "price" | "rating" | "seller") => {
    setSortBy(value);
    filterAndSort(products, searchTerm, value);
  };

  const handleRefresh = () => {
    window.location.reload();
  };

  const downloadExcel = async () => {
    if (!history || history.length === 0) {
      toast.error("Henüz rapor yok");
      return;
    }

    const latestReport = history[0];
    if (latestReport.reportUrl) {
      window.open(latestReport.reportUrl, "_blank");
    } else {
      toast.error("Rapor linki bulunamadı");
    }
  };

  const getPriceChange = (original: number, final: number) => {
    const change = ((original - final) / original) * 100;
    return change > 0 ? change.toFixed(1) : "0";
  };

  const getAveragePrice = () => {
    if (filteredProducts.length === 0) return 0;
    const sum = filteredProducts.reduce((acc, p) => acc + p.finalPrice, 0);
    return (sum / filteredProducts.length).toFixed(2);
  };

  const getLowestPrice = () => {
    if (filteredProducts.length === 0) return 0;
    return Math.min(...filteredProducts.map((p) => p.finalPrice));
  };

  const getHighestPrice = () => {
    if (filteredProducts.length === 0) return 0;
    return Math.max(...filteredProducts.map((p) => p.finalPrice));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Fiyat Karşılaştırması</h1>
        <p className="text-muted-foreground mt-2">
          Trendyol mağazasındaki ürünlerin fiyat ve satıcı karşılaştırması
        </p>
      </div>

      {/* İstatistikler */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Toplam Ürün</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{filteredProducts.length}</div>
            <p className="text-xs text-muted-foreground">Filtrelenen ürün sayısı</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Ortalama Fiyat</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">₺{getAveragePrice()}</div>
            <p className="text-xs text-muted-foreground">Seçili ürünlerin ortalaması</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">En Düşük Fiyat</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">₺{getLowestPrice()}</div>
            <p className="text-xs text-muted-foreground">Minimum fiyat</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">En Yüksek Fiyat</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">₺{getHighestPrice()}</div>
            <p className="text-xs text-muted-foreground">Maksimum fiyat</p>
          </CardContent>
        </Card>
      </div>

      {/* Arama ve Sıralama */}
      <Card>
        <CardHeader>
          <CardTitle>Filtreler</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <Input
                placeholder="Ürün adı veya satıcı ara..."
                value={searchTerm}
                onChange={(e) => handleSearch(e.target.value)}
              />
            </div>
            <div className="flex gap-2">
              <Button
                variant={sortBy === "price" ? "default" : "outline"}
                onClick={() => handleSort("price")}
                size="sm"
              >
                Fiyata Göre
              </Button>
              <Button
                variant={sortBy === "rating" ? "default" : "outline"}
                onClick={() => handleSort("rating")}
                size="sm"
              >
                Puanına Göre
              </Button>
              <Button
                variant={sortBy === "seller" ? "default" : "outline"}
                onClick={() => handleSort("seller")}
                size="sm"
              >
                Satıcıya Göre
              </Button>
              <Button
                variant="outline"
                onClick={handleRefresh}
                size="sm"
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tablo */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Ürün Listesi</CardTitle>
            <CardDescription>
              {filteredProducts.length} ürün gösteriliyor
            </CardDescription>
          </div>
          <Button
            onClick={downloadExcel}
            disabled={isLoading}
            size="sm"
          >
            <Download className="h-4 w-4 mr-2" />
            Excel İndir
          </Button>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center h-96">
              <Loader2 className="animate-spin" />
            </div>
          ) : filteredProducts.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4 font-semibold">Ürün Adı</th>
                    <th className="text-left py-3 px-4 font-semibold">Satıcı</th>
                    <th className="text-right py-3 px-4 font-semibold">Orijinal Fiyat</th>
                    <th className="text-left py-3 px-4 font-semibold">Kupon</th>
                    <th className="text-right py-3 px-4 font-semibold">Son Fiyat</th>
                    <th className="text-center py-3 px-4 font-semibold">İndirim</th>
                    <th className="text-center py-3 px-4 font-semibold">Puan</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredProducts.map((product, idx) => (
                    <tr key={idx} className="border-b hover:bg-muted/50 transition-colors">
                      <td className="py-3 px-4">
                        <a
                          href={product.productLink}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline font-medium truncate"
                          title={product.productName}
                        >
                          {product.productName.length > 40
                            ? product.productName.substring(0, 40) + "..."
                            : product.productName}
                        </a>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant="secondary">{product.seller}</Badge>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <span className="line-through text-muted-foreground">
                          ₺{product.originalPrice.toFixed(2)}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        {product.coupon ? (
                          <Badge className="bg-green-100 text-green-800">
                            {product.coupon}
                          </Badge>
                        ) : (
                          <span className="text-muted-foreground text-xs">-</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right font-semibold">
                        ₺{product.finalPrice.toFixed(2)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <TrendingDown className="h-4 w-4 text-green-600" />
                          <span className="text-green-600 font-semibold">
                            %{getPriceChange(product.originalPrice, product.finalPrice)}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <Badge className="bg-yellow-100 text-yellow-800">
                          {product.rating.toFixed(1)} ⭐
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12">
              <p className="text-muted-foreground">
                {products.length === 0
                  ? "Henüz rapor yok. Workflow'u çalıştırın."
                  : "Arama kriterlerine uygun ürün bulunamadı."}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

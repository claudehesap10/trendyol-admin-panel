"use client";
import { useState, useEffect } from "react";
import { useLocation } from "wouter";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, TrendingUp, TrendingDown, Minus, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { Line, Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
);

interface ReportData {
  "Ürün Adı"?: string;
  "Satıcı"?: string;
  "Son Fiyat (TL)"?: number;
  "Rating"?: number;
}

const MY_STORE_NAME = "Esvento"; // Kendi mağaza isminiz

export default function TrendAnalysis() {
  const [, setLocation] = useLocation();
  const [data, setData] = useState<ReportData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedProduct, setSelectedProduct] = useState<string>("");
  const [productNames, setProductNames] = useState<string[]>([]);

  // Backend'den rapor çek
  const fetchReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/reports/latest");
      if (!response.ok) throw new Error("Rapor yüklenemedi");

      const result = await response.json();
      if (result?.data && Array.isArray(result.data)) {
        setData(result.data);
        const products = Array.from(
          new Set(result.data.map((item: ReportData) => item["Ürün Adı"]).filter(Boolean))
        ) as string[];
        setProductNames(products);
        if (products.length > 0) {
          setSelectedProduct(products[0]);
        }
      }
    } catch (err) {
      setError("Rapor yüklenirken hata oluştu");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // İlk yüklemede rapor çek
  useEffect(() => {
    fetchReport();
  }, []);

  // Seçili ürünün verilerini hazırla
  const getProductData = () => {
    if (!selectedProduct) return null;

    const productData = data.filter((item) => item["Ürün Adı"] === selectedProduct);
    const sellers = Array.from(new Set(productData.map((item) => item["Satıcı"]).filter(Boolean))) as string[];

    // Satıcılar bazında fiyatları grupla
    const sellerPrices: { [key: string]: number } = {};
    const sellerRatings: { [key: string]: number } = {};
    
    productData.forEach((item) => {
      const seller = item["Satıcı"] || "Bilinmiyor";
      const price = item["Son Fiyat (TL)"] || 0;
      const rating = item["Rating"] || 0;
      
      if (!sellerPrices[seller] || price < sellerPrices[seller]) {
        sellerPrices[seller] = price;
        sellerRatings[seller] = rating;
      }
    });

    return {
      sellers,
      prices: sellers.map((seller) => sellerPrices[seller] || 0),
      ratings: sellers.map((seller) => sellerRatings[seller] || 0),
    };
  };

  const productData = getProductData();

  // Benim mağazamın durumu
  const getMyStoreComparison = () => {
    if (!productData) return null;

    const myIndex = productData.sellers.findIndex(s => s.toUpperCase().includes(MY_STORE_NAME.toUpperCase()));
    if (myIndex === -1) return null;

    const myPrice = productData.prices[myIndex];
    const myRating = productData.ratings[myIndex];
    const otherPrices = productData.prices.filter((_, i) => i !== myIndex);
    const otherRatings = productData.ratings.filter((_, i) => i !== myIndex);

    const avgPrice = otherPrices.reduce((a, b) => a + b, 0) / otherPrices.length;
    const minPrice = Math.min(...otherPrices);
    const maxPrice = Math.max(...otherPrices);
    const avgRating = otherRatings.reduce((a, b) => a + b, 0) / otherRatings.length;

    const priceDiff = myPrice - avgPrice;
    const priceDiffPercent = ((priceDiff / avgPrice) * 100).toFixed(1);
    const cheaperThanCount = otherPrices.filter(p => p > myPrice).length;
    const expensiveThanCount = otherPrices.filter(p => p < myPrice).length;

    return {
      myPrice,
      myRating,
      avgPrice: avgPrice.toFixed(2),
      minPrice: minPrice.toFixed(2),
      maxPrice: maxPrice.toFixed(2),
      avgRating: avgRating.toFixed(1),
      priceDiff: Math.abs(priceDiff).toFixed(2),
      priceDiffPercent,
      isExpensive: priceDiff > 0,
      isCheaper: priceDiff < 0,
      cheaperThanCount,
      expensiveThanCount,
      totalCompetitors: otherPrices.length,
    };
  };

  const comparison = getMyStoreComparison();

  // Chart verilerini daha okunabilir hale getir - Y eksenini dinamik yapılandır
  const priceChartData = productData
    ? {
        labels: productData.sellers.map(s => s.length > 20 ? s.substring(0, 17) + '...' : s),
        datasets: [
          {
            label: "Fiyat (₺)",
            data: productData.prices,
            backgroundColor: productData.sellers.map(s => 
              s.toUpperCase().includes(MY_STORE_NAME.toUpperCase()) 
                ? "rgba(34, 197, 94, 0.7)" // Yeşil - benim mağazam
                : "rgba(99, 102, 241, 0.7)" // Mavi - diğerleri
            ),
            borderColor: productData.sellers.map(s => 
              s.toUpperCase().includes(MY_STORE_NAME.toUpperCase()) 
                ? "rgba(34, 197, 94, 1)"
                : "rgba(99, 102, 241, 1)"
            ),
            borderWidth: 2,
          },
        ],
      }
    : null;

  const ratingChartData = productData
    ? {
        labels: productData.sellers.map(s => s.length > 20 ? s.substring(0, 17) + '...' : s),
        datasets: [
          {
            label: "Rating (⭐)",
            data: productData.ratings,
            borderColor: "rgba(251, 146, 60, 1)",
            backgroundColor: "rgba(251, 146, 60, 0.1)",
            borderWidth: 3,
            fill: true,
            tension: 0.4,
            pointBackgroundColor: productData.sellers.map(s => 
              s.toUpperCase().includes(MY_STORE_NAME.toUpperCase()) 
                ? "rgba(34, 197, 94, 1)"
                : "rgba(251, 146, 60, 1)"
            ),
            pointBorderColor: "#fff",
            pointBorderWidth: 2,
            pointRadius: 6,
            pointHoverRadius: 8,
          },
        ],
      }
    : null;

  // Dinamik Y ekseni ayarları
  const priceChartOptions: ChartOptions<'bar'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: "top",
        labels: {
          font: { size: 12, weight: 'bold' },
          padding: 15,
        }
      },
      title: {
        display: false,
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        padding: 12,
        titleFont: { size: 14, weight: 'bold' },
        bodyFont: { size: 13 },
        callbacks: {
          label: (context) => {
            const label = context.dataset.label || '';
            const value = context.parsed.y;
            return `${label}: ${value?.toFixed(2) ?? '0.00'} ₺`;
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: false,
        ticks: {
          callback: (value) => `${value} ₺`,
          font: { size: 11 }
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
        }
      },
      x: {
        ticks: {
          font: { size: 10 },
          maxRotation: 45,
          minRotation: 45,
        },
        grid: {
          display: false,
        }
      },
    },
  };

  const ratingChartOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: "top",
        labels: {
          font: { size: 12, weight: 'bold' },
          padding: 15,
        }
      },
      title: {
        display: false,
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        padding: 12,
        titleFont: { size: 14, weight: 'bold' },
        bodyFont: { size: 13 },
        callbacks: {
          label: (context) => {
            const label = context.dataset.label || '';
            const value = context.parsed.y;
            return `${label}: ${value?.toFixed(1) ?? '0.0'} / 5.0`;
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 5,
        ticks: {
          stepSize: 1,
          callback: (value) => `${value} ⭐`,
          font: { size: 11 }
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.05)',
        }
      },
      x: {
        ticks: {
          font: { size: 10 },
          maxRotation: 45,
          minRotation: 45,
        },
        grid: {
          display: false,
        }
      },
    },
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6 space-y-6">
        <Card>
          <CardHeader>
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-4 w-96 mt-2" />
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-10 w-full max-w-md" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Skeleton className="h-80 w-full" />
              <Skeleton className="h-80 w-full" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header with Back Button */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button 
            variant="outline" 
            size="icon"
            onClick={() => setLocation("/reports")}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">📈 Trend Analizi</h1>
            <p className="text-muted-foreground">Ürün fiyat ve satıcı karşılaştırması</p>
          </div>
        </div>
        <Button onClick={fetchReport} variant="outline">
          Yenile
        </Button>
      </div>

      {/* Error State */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Product Selector */}
      <Card>
        <CardHeader>
          <CardTitle>Ürün Seçimi</CardTitle>
          <CardDescription>Analiz etmek istediğiniz ürünü seçin</CardDescription>
        </CardHeader>
        <CardContent>
          <Select value={selectedProduct} onValueChange={setSelectedProduct}>
            <SelectTrigger className="max-w-md">
              <SelectValue placeholder="Bir ürün seçin..." />
            </SelectTrigger>
            <SelectContent>
              {productNames.map((name) => (
                <SelectItem key={name} value={name}>
                  {name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {/* Comparison Summary Cards */}
      {comparison && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Fiyat Durumu
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-2xl font-bold">{comparison.myPrice.toFixed(2)} ₺</div>
                  <p className="text-xs text-muted-foreground mt-1">Senin fiyatın</p>
                </div>
                {comparison.isExpensive ? (
                  <div className="flex items-center gap-1 text-red-600">
                    <TrendingUp className="h-5 w-5" />
                    <span className="text-sm font-semibold">+{comparison.priceDiffPercent}%</span>
                  </div>
                ) : comparison.isCheaper ? (
                  <div className="flex items-center gap-1 text-green-600">
                    <TrendingDown className="h-5 w-5" />
                    <span className="text-sm font-semibold">{comparison.priceDiffPercent}%</span>
                  </div>
                ) : (
                  <Minus className="h-5 w-5 text-gray-400" />
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Rekabet Durumu
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm">Daha ucuz</span>
                  <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                    <ArrowDownRight className="h-3 w-3 mr-1" />
                    {comparison.cheaperThanCount} satıcı
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Daha pahalı</span>
                  <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
                    <ArrowUpRight className="h-3 w-3 mr-1" />
                    {comparison.expensiveThanCount} satıcı
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Piyasa Ortalaması
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div>
                  <div className="text-2xl font-bold">{comparison.avgPrice} ₺</div>
                  <p className="text-xs text-muted-foreground">Ortalama fiyat</p>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Badge variant="secondary" className="text-xs">
                    Min: {comparison.minPrice} ₺
                  </Badge>
                  <Badge variant="secondary" className="text-xs">
                    Max: {comparison.maxPrice} ₺
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Rating Durumu
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div>
                  <div className="text-2xl font-bold flex items-center gap-2">
                    {comparison.myRating.toFixed(1)} <span className="text-yellow-500">⭐</span>
                  </div>
                  <p className="text-xs text-muted-foreground">Senin rating'in</p>
                </div>
                <div className="text-sm text-muted-foreground">
                  Ortalama: {comparison.avgRating} ⭐
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Insight Banner */}
      {comparison && (
        <Alert className={comparison.isExpensive ? "border-orange-200 bg-orange-50" : "border-green-200 bg-green-50"}>
          <AlertDescription className="text-sm">
            {comparison.isExpensive ? (
              <span className="font-medium text-orange-900">
                💡 Fiyatın rakiplerden ortalama <strong>{comparison.priceDiff} ₺</strong> ({comparison.priceDiffPercent}%) daha yüksek. 
                Fiyat düşürmeyi düşünebilirsin! {comparison.cheaperThanCount} satıcıdan daha pahalısın.
              </span>
            ) : comparison.isCheaper ? (
              <span className="font-medium text-green-900">
                ✅ Harika! Fiyatın rakiplerden ortalama <strong>{comparison.priceDiff} ₺</strong> ({Math.abs(parseFloat(comparison.priceDiffPercent))}%) daha ucuz. 
                {comparison.cheaperThanCount} satıcıdan daha ucuzsun!
              </span>
            ) : (
              <span className="font-medium text-blue-900">
                ℹ️ Fiyatın piyasa ortalamasına yakın.
              </span>
            )}
          </AlertDescription>
        </Alert>
      )}

      {/* Charts */}
      {productData ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                💰 Fiyat Karşılaştırması
              </CardTitle>
              <CardDescription>
                Satıcılar arasında fiyat dağılımı ({productData.sellers.length} satıcı)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[400px]">
                {priceChartData && <Bar data={priceChartData} options={priceChartOptions} />}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                ⭐ Rating Karşılaştırması
              </CardTitle>
              <CardDescription>
                Satıcılar arasında müşteri memnuniyeti karşılaştırması
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-[400px]">
                {ratingChartData && <Line data={ratingChartData} options={ratingChartOptions} />}
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <Card>
          <CardContent className="flex items-center justify-center h-64">
            <div className="text-center text-muted-foreground">
              <p className="text-lg font-medium">Veri bulunamadı</p>
              <p className="text-sm">Lütfen bir ürün seçin</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

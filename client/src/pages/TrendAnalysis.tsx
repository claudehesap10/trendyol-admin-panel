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
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4 md:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-4">
            <Button 
              variant="ghost" 
              size="icon"
              onClick={() => setLocation("/reports")}
              className="hover:bg-white/80"
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                Trend Analizi
              </h1>
              <p className="text-sm text-muted-foreground mt-1">Rakiplerinle kıyasla, stratejini belirle</p>
            </div>
          </div>
          <Button onClick={fetchReport} variant="outline" className="bg-white">
            Yenile
          </Button>
        </div>

        {/* Error State */}
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Product Selector - Daha prominent */}
        <Card className="border-2 border-indigo-100 shadow-lg">
          <CardContent className="pt-6">
            <div className="space-y-3">
              <label className="text-sm font-semibold text-slate-700">Analiz edilecek ürün</label>
              <Select value={selectedProduct} onValueChange={setSelectedProduct}>
                <SelectTrigger className="h-12 text-base">
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
            </div>
          </CardContent>
        </Card>

        {/* Comparison Summary Cards - Daha minimal ve şık */}
        {comparison && (
          <>
            {/* Insight Banner - Önce göster */}
            <Alert className={`border-2 ${
              comparison.isExpensive 
                ? "border-amber-200 bg-gradient-to-r from-amber-50 to-orange-50" 
                : "border-emerald-200 bg-gradient-to-r from-emerald-50 to-green-50"
            }`}>
              <AlertDescription className="text-sm leading-relaxed">
                {comparison.isExpensive ? (
                  <div className="flex items-start gap-3">
                    <div className="text-2xl">⚠️</div>
                    <div>
                      <p className="font-semibold text-amber-900 mb-1">Fiyat Uyarısı</p>
                      <p className="text-amber-800">
                        Fiyatın rakiplerden ortalama <span className="font-bold">{comparison.priceDiff} ₺</span> ({comparison.priceDiffPercent}%) daha yüksek. 
                        <span className="block mt-1">🎯 {comparison.cheaperThanCount} satıcıdan daha ucuza satış yapabilirsin!</span>
                      </p>
                    </div>
                  </div>
                ) : comparison.isCheaper ? (
                  <div className="flex items-start gap-3">
                    <div className="text-2xl">🎉</div>
                    <div>
                      <p className="font-semibold text-emerald-900 mb-1">Harika Fiyat!</p>
                      <p className="text-emerald-800">
                        Fiyatın rakiplerden ortalama <span className="font-bold">{comparison.priceDiff} ₺</span> ({Math.abs(parseFloat(comparison.priceDiffPercent))}%) daha ucuz. 
                        <span className="block mt-1">✨ {comparison.cheaperThanCount} satıcıyı geride bırakıyorsun!</span>
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start gap-3">
                    <div className="text-2xl">ℹ️</div>
                    <div>
                      <p className="font-semibold text-blue-900 mb-1">Dengeli Fiyat</p>
                      <p className="text-blue-800">Fiyatın piyasa ortalamasına oldukça yakın.</p>
                    </div>
                  </div>
                )}
              </AlertDescription>
            </Alert>

            {/* Stats Grid - 3 kolon */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Benim Fiyatım */}
              <Card className="relative overflow-hidden border-2 border-indigo-100 hover:shadow-xl transition-all duration-300">
                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-indigo-500/10 to-purple-500/10 rounded-bl-full" />
                <CardContent className="pt-6">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-indigo-600 uppercase tracking-wide">Senin Fiyatın</span>
                      {comparison.isExpensive ? (
                        <Badge variant="destructive" className="text-xs">Yüksek</Badge>
                      ) : comparison.isCheaper ? (
                        <Badge className="bg-green-500 text-xs">İyi</Badge>
                      ) : (
                        <Badge variant="secondary" className="text-xs">Normal</Badge>
                      )}
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-4xl font-bold text-slate-900">{comparison.myPrice.toFixed(2)}</span>
                      <span className="text-lg text-slate-500">₺</span>
                    </div>
                    {comparison.isExpensive ? (
                      <div className="flex items-center gap-1 text-red-600 text-sm font-semibold">
                        <TrendingUp className="h-4 w-4" />
                        <span>Ort. +{comparison.priceDiffPercent}%</span>
                      </div>
                    ) : comparison.isCheaper ? (
                      <div className="flex items-center gap-1 text-green-600 text-sm font-semibold">
                        <TrendingDown className="h-4 w-4" />
                        <span>Ort. {comparison.priceDiffPercent}%</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1 text-slate-400 text-sm">
                        <Minus className="h-4 w-4" />
                        <span>Ortalama seviyede</span>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Piyasa Ortalaması */}
              <Card className="relative overflow-hidden border-2 border-slate-100 hover:shadow-xl transition-all duration-300">
                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-slate-500/10 to-slate-600/10 rounded-bl-full" />
                <CardContent className="pt-6">
                  <div className="space-y-3">
                    <span className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Piyasa Ortalaması</span>
                    <div className="flex items-baseline gap-2">
                      <span className="text-4xl font-bold text-slate-900">{comparison.avgPrice}</span>
                      <span className="text-lg text-slate-500">₺</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="outline" className="text-xs border-emerald-200 text-emerald-700 bg-emerald-50">
                        Min {comparison.minPrice}₺
                      </Badge>
                      <Badge variant="outline" className="text-xs border-rose-200 text-rose-700 bg-rose-50">
                        Max {comparison.maxPrice}₺
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Rekabet Pozisyonu */}
              <Card className="relative overflow-hidden border-2 border-amber-100 hover:shadow-xl transition-all duration-300">
                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-amber-500/10 to-orange-500/10 rounded-bl-full" />
                <CardContent className="pt-6">
                  <div className="space-y-3">
                    <span className="text-xs font-semibold text-amber-600 uppercase tracking-wide">Rekabet Durumu</span>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between bg-green-50 rounded-lg p-2">
                        <span className="text-xs font-medium text-green-700">Senden ucuz</span>
                        <div className="flex items-center gap-1">
                          <ArrowDownRight className="h-3 w-3 text-green-600" />
                          <span className="text-lg font-bold text-green-700">{comparison.expensiveThanCount}</span>
                        </div>
                      </div>
                      <div className="flex items-center justify-between bg-red-50 rounded-lg p-2">
                        <span className="text-xs font-medium text-red-700">Senden pahalı</span>
                        <div className="flex items-center gap-1">
                          <ArrowUpRight className="h-3 w-3 text-red-600" />
                          <span className="text-lg font-bold text-red-700">{comparison.cheaperThanCount}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </>
        )}

        {/* Charts - Sadece Fiyat */}
        {productData ? (
          <Card className="border-2 border-slate-100 shadow-lg">
            <CardHeader className="border-b bg-gradient-to-r from-blue-50 to-indigo-50">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-500 flex items-center justify-center text-white text-xl">
                  💰
                </div>
                <div>
                  <CardTitle className="text-lg">Fiyat Karşılaştırması</CardTitle>
                  <CardDescription className="text-xs">
                    {productData.sellers.length} satıcı arasında fiyat dağılımı
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="h-[600px]">
                {priceChartData && <Bar data={priceChartData} options={priceChartOptions} />}
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card className="border-2 border-dashed border-slate-200">
            <CardContent className="flex flex-col items-center justify-center h-64 text-center">
              <div className="text-6xl mb-4">📊</div>
              <p className="text-lg font-medium text-slate-700">Veri bulunamadı</p>
              <p className="text-sm text-muted-foreground mt-1">Lütfen yukarıdan bir ürün seçin</p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

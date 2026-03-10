"use client";
import { useState, useEffect } from "react";
import { Card, Spin, Empty, message, Row, Col, Select, Button, Table, Tag, Space, Statistic } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { Line, Bar } from "react-chartjs-2";
import { useNavigate } from "wouter";
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

export default function TrendAnalysis() {
  const [data, setData] = useState<ReportData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedProduct, setSelectedProduct] = useState<string>("");
  const [productNames, setProductNames] = useState<string[]>([]);
  const [navigate] = useNavigate();

  // Backend'den rapor çek
  const fetchReport = async () => {
    setLoading(true);
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
    } catch (error) {
      message.error("Rapor yüklenirken hata oluştu");
      console.error(error);
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
      }
      sellerRatings[seller] = rating;
    });

    const prices = sellers.map((seller) => sellerPrices[seller] || 0);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const avgPrice = prices.reduce((a, b) => a + b, 0) / prices.length;

    return {
      sellers,
      prices,
      ratings: sellers.map((seller) => sellerRatings[seller] || 0),
      minPrice,
      maxPrice,
      avgPrice,
      sellerPrices,
      sellerRatings,
    };
  };

  const productData = getProductData();

  // Fiyat karşılaştırması chart'ı - dinamik ölçeklendirme
  const priceChartData = productData
    ? {
        labels: productData.sellers,
        datasets: [
          {
            label: "Fiyat (TL)",
            data: productData.prices,
            backgroundColor: productData.sellers.map((seller) => 
              seller === "1126746" ? "rgba(255, 193, 7, 0.8)" : "rgba(75, 192, 192, 0.6)"
            ),
            borderColor: productData.sellers.map((seller) => 
              seller === "1126746" ? "rgba(255, 193, 7, 1)" : "rgba(75, 192, 192, 1)"
            ),
            borderWidth: 2,
          },
        ],
      }
    : null;

  // Rating karşılaştırması chart'ı
  const ratingChartData = productData
    ? {
        labels: productData.sellers,
        datasets: [
          {
            label: "Rating (⭐)",
            data: productData.ratings,
            borderColor: "rgba(255, 193, 7, 1)",
            backgroundColor: "rgba(255, 193, 7, 0.2)",
            borderWidth: 2,
            fill: true,
            tension: 0.4,
          },
        ],
      }
    : null;

  // Dinamik Y eksenini hesapla (fiyat farkları küçükse daha iyi görünüm için)
  const getPriceChartOptions = () => {
    if (!productData) return {};
    
    const padding = (productData.maxPrice - productData.minPrice) * 0.1;
    const min = Math.max(0, productData.minPrice - padding);
    const max = productData.maxPrice + padding;

    return {
      responsive: true,
      plugins: {
        legend: {
          position: "top" as const,
        },
        title: {
          display: false,
        },
        tooltip: {
          callbacks: {
            label: function(context: any) {
              return `${context.parsed.y.toFixed(2)} TL`;
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: false,
          min: min,
          max: max,
          ticks: {
            callback: function(value: any) {
              return `${value.toFixed(2)} TL`;
            }
          }
        },
      },
    };
  };

  const ratingChartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: "top" as const,
      },
      title: {
        display: false,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 10,
        ticks: {
          callback: function(value: any) {
            return `${value.toFixed(1)} ⭐`;
          }
        }
      },
    },
  };

  // Tablo verisi
  const tableData = productData
    ? productData.sellers.map((seller, index) => ({
        key: index,
        seller: seller === "1126746" ? `${seller} (Sizin Mağaza)` : seller,
        price: productData.prices[index],
        rating: productData.ratings[index],
        difference: productData.minPrice < productData.prices[index] ? productData.prices[index] - productData.minPrice : 0,
      }))
    : [];

  const tableColumns = [
    {
      title: "Satıcı",
      dataIndex: "seller",
      key: "seller",
      render: (text: string) => {
        if (text.includes("Sizin Mağaza")) {
          return <Tag color="gold">{text}</Tag>;
        }
        return text;
      }
    },
    {
      title: "Fiyat (TL)",
      dataIndex: "price",
      key: "price",
      render: (price: number) => `${price.toFixed(2)} TL`,
      sorter: (a: any, b: any) => a.price - b.price,
    },
    {
      title: "Rating",
      dataIndex: "rating",
      key: "rating",
      render: (rating: number) => `${rating.toFixed(1)} ⭐`,
      sorter: (a: any, b: any) => a.rating - b.rating,
    },
    {
      title: "Fiyat Farkı",
      dataIndex: "difference",
      key: "difference",
      render: (diff: number) => {
        if (diff === 0) {
          return <Tag color="green">En Düşük</Tag>;
        }
        return <span style={{ color: "#ff4d4f" }}>+{diff.toFixed(2)} TL</span>;
      },
      sorter: (a: any, b: any) => a.difference - b.difference,
    },
  ];

  return (
    <div style={{ padding: "20px", minHeight: "100vh", backgroundColor: "#f5f5f5" }}>
      {/* Geri Dönüş Butonu */}
      <Button 
        type="primary" 
        icon={<ArrowLeftOutlined />} 
        onClick={() => navigate("/reports")}
        style={{ marginBottom: "20px" }}
      >
        Raporlara Dön
      </Button>

      <Card style={{ marginBottom: "20px" }}>
        <h1 style={{ marginBottom: "10px" }}>📈 Trend Analizi</h1>
        <p style={{ color: "#666", marginBottom: "20px" }}>Ürün fiyat ve satıcı karşılaştırması</p>

        <div style={{ marginBottom: 20 }}>
          <Select
            placeholder="Ürün Seç"
            value={selectedProduct || undefined}
            onChange={setSelectedProduct}
            style={{ width: "100%", maxWidth: "400px" }}
            options={productNames.map((name) => ({ label: name, value: name }))}
          />
        </div>

        <Spin spinning={loading} description="Rapor yükleniyor...">
          {productData ? (
            <>
              {/* Özet Bilgi Kartları */}
              <Row gutter={[16, 16]} style={{ marginBottom: "30px" }}>
                <Col xs={24} sm={8}>
                  <Card style={{ textAlign: "center", backgroundColor: "#f0f5ff", border: "1px solid #b6e3ff" }}>
                    <Statistic
                      title="En Düşük Fiyat"
                      value={productData.minPrice}
                      precision={2}
                      suffix="TL"
                      valueStyle={{ color: "#1890ff" }}
                    />
                  </Card>
                </Col>
                <Col xs={24} sm={8}>
                  <Card style={{ textAlign: "center", backgroundColor: "#fffbe6", border: "1px solid #ffe58f" }}>
                    <Statistic
                      title="Ortalama Fiyat"
                      value={productData.avgPrice}
                      precision={2}
                      suffix="TL"
                      valueStyle={{ color: "#faad14" }}
                    />
                  </Card>
                </Col>
                <Col xs={24} sm={8}>
                  <Card style={{ textAlign: "center", backgroundColor: "#f6ffed", border: "1px solid #b7eb8f" }}>
                    <Statistic
                      title="Fiyat Aralığı"
                      value={productData.maxPrice - productData.minPrice}
                      precision={2}
                      suffix="TL"
                      valueStyle={{ color: "#52c41a" }}
                    />
                  </Card>
                </Col>
              </Row>

              {/* Grafikler */}
              <Row gutter={[20, 20]} style={{ marginBottom: "30px" }}>
                <Col xs={24} md={12}>
                  <Card title="💰 Satıcı Bazında Fiyat Karşılaştırması" bordered={false} style={{ boxShadow: "0 2px 8px rgba(0,0,0,0.1)" }}>
                    {priceChartData && <Bar data={priceChartData} options={getPriceChartOptions()} />}
                  </Card>
                </Col>
                <Col xs={24} md={12}>
                  <Card title="⭐ Satıcı Bazında Rating Karşılaştırması" bordered={false} style={{ boxShadow: "0 2px 8px rgba(0,0,0,0.1)" }}>
                    {ratingChartData && <Line data={ratingChartData} options={ratingChartOptions} />}
                  </Card>
                </Col>
              </Row>

              {/* Detaylı Tablo */}
              <Card title="📊 Detaylı Satıcı Bilgileri" bordered={false} style={{ boxShadow: "0 2px 8px rgba(0,0,0,0.1)" }}>
                <Table 
                  columns={tableColumns} 
                  dataSource={tableData}
                  pagination={{ pageSize: 10 }}
                  size="middle"
                />
              </Card>
            </>
          ) : (
            <Empty description="Veri bulunamadı" />
          )}
        </Spin>
      </Card>
    </div>
  );
}

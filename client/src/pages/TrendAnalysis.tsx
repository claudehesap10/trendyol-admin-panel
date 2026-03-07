"use client";
import { useState, useEffect } from "react";
import { Card, Spin, Empty, message, Row, Col, Select } from "antd";
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
    productData.forEach((item) => {
      const seller = item["Satıcı"] || "Bilinmiyor";
      const price = item["Son Fiyat (TL)"] || 0;
      if (!sellerPrices[seller] || price < sellerPrices[seller]) {
        sellerPrices[seller] = price;
      }
    });

    return {
      sellers,
      prices: sellers.map((seller) => sellerPrices[seller] || 0),
      ratings: sellers.map((seller) => {
        const item = productData.find((d) => d["Satıcı"] === seller);
        return item?.["Rating"] || 0;
      }),
    };
  };

  const productData = getProductData();

  // Fiyat karşılaştırması chart'ı
  const priceChartData = productData
    ? {
        labels: productData.sellers,
        datasets: [
          {
            label: "Fiyat (TL)",
            data: productData.prices,
            backgroundColor: "rgba(75, 192, 192, 0.6)",
            borderColor: "rgba(75, 192, 192, 1)",
            borderWidth: 1,
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

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: "top" as const,
      },
      title: {
        display: true,
        text: "Ürün Analizi",
      },
    },
    scales: {
      y: {
        beginAtZero: true,
      },
    },
  };

  return (
    <div style={{ padding: "20px" }}>
      <Card>
        <h1>📈 Trend Analizi</h1>
        <p>Ürün fiyat ve satıcı karşılaştırması</p>

        <div style={{ marginBottom: 20 }}>
          <Select
            placeholder="Ürün Seç"
            value={selectedProduct || undefined}
            onChange={setSelectedProduct}
            style={{ width: "300px" }}
            options={productNames.map((name) => ({ label: name, value: name }))}
          />
        </div>

        <Spin spinning={loading} description="Rapor yükleniyor...">
          {productData ? (
            <Row gutter={[20, 20]}>
              <Col xs={24} md={12}>
                <Card title="Satıcı Bazında Fiyat Karşılaştırması">
                  {priceChartData && <Bar data={priceChartData} options={chartOptions} />}
                </Card>
              </Col>
              <Col xs={24} md={12}>
                <Card title="Satıcı Bazında Rating Karşılaştırması">
                  {ratingChartData && <Line data={ratingChartData} options={chartOptions} />}
                </Card>
              </Col>
            </Row>
          ) : (
            <Empty description="Veri bulunamadı" />
          )}
        </Spin>
      </Card>
    </div>
  );
}

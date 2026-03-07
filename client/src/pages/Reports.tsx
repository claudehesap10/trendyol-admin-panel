"use client";
import { useState, useEffect } from "react";
import { Table, Button, Input, Space, Spin, Empty, message, Card, Select, Tag } from "antd";
import { DownloadOutlined, ReloadOutlined, FilterOutlined } from "@ant-design/icons";
import * as XLSX from "xlsx";
import "./Reports.css";

interface ReportData {
  key?: string;
  "Ürün Adı"?: string;
  "Ürün Linki"?: string;
  "Satıcı"?: string;
  "Orijinal Fiyat (TL)"?: number;
  "Kupon İndirimi"?: string;
  "Sepette İndirimi"?: string;
  "Son Fiyat (TL)"?: number;
  "Rating"?: number;
  "Notlar"?: string;
  isBestPrice?: boolean;
}

export default function Reports() {
  const [data, setData] = useState<ReportData[]>([]);
  const [filteredData, setFilteredData] = useState<ReportData[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState("");
  const [selectedProduct, setSelectedProduct] = useState<string>("");
  const [selectedSeller, setSelectedSeller] = useState<string>("");

  // Backend'den rapor çek
  const fetchReport = async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/reports/latest");
      if (!response.ok) throw new Error("Rapor yüklenemedi");

      const result = await response.json();
      if (result?.data && Array.isArray(result.data)) {
        // Best price hesapla
        const productPrices: { [key: string]: number } = {};
        result.data.forEach((item: ReportData) => {
          const productName = item["Ürün Adı"] || "";
          const price = item["Son Fiyat (TL)"] || 0;
          if (productName && (!productPrices[productName] || price < productPrices[productName])) {
            productPrices[productName] = price;
          }
        });

        const dataWithKeys = result.data.map((item: ReportData, index: number) => {
          const productName = item["Ürün Adı"] || "";
          return {
            ...item,
            key: `${index}`,
            isBestPrice: item["Son Fiyat (TL)"] === productPrices[productName],
          };
        });
        setData(dataWithKeys);
        setFilteredData(dataWithKeys);
        message.success(`${dataWithKeys.length} ürün yüklendi`);
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

  // Filtreleme
  useEffect(() => {
    let filtered = data;

    // Ürün adı filtresi
    if (selectedProduct) {
      filtered = filtered.filter((item) => item["Ürün Adı"] === selectedProduct);
    }

    // Satıcı filtresi
    if (selectedSeller) {
      filtered = filtered.filter((item) => item["Satıcı"] === selectedSeller);
    }

    // Arama filtresi
    if (searchText) {
      filtered = filtered.filter((item) =>
        Object.values(item).some(
          (val) =>
            val &&
            val.toString().toLowerCase().includes(searchText.toLowerCase())
        )
      );
    }

    setFilteredData(filtered);
  }, [selectedProduct, selectedSeller, searchText, data]);

  // Excel indir
  const downloadExcel = () => {
    if (data.length === 0) {
      message.warning("İndirilecek veri yok");
      return;
    }

    const exportData = data.map(({ key, isBestPrice, ...rest }) => rest);
    const ws = XLSX.utils.json_to_sheet(exportData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Rapor");
    XLSX.writeFile(wb, "trendyol_rapor.xlsx");
    message.success("Excel dosyası indirildi");
  };

  // Ürün adı listesi
  const productNames = Array.from(new Set(data.map((item) => item["Ürün Adı"]).filter(Boolean))) as string[];

  // Satıcı listesi
  const sellers = Array.from(new Set(data.map((item) => item["Satıcı"]).filter(Boolean))) as string[];

  // Son tarama süresi
  const getLastScanTime = () => {
    if (data.length === 0) return "Veri yok";
    // Backend'den gelen en son release tarihi
    const now = new Date();
    // İlk veri yüklenme zamanı (simule edilmiş)
    return now.toLocaleString('tr-TR');
  };

  // Ürün grupları oluştur (tüm data üzerinde)
  const getProductGroups = () => {
    const groups: { [key: string]: number } = {};
    data.forEach((item) => {
      const productName = item["Ürün Adı"] || "";
      groups[productName] = (groups[productName] || 0) + 1;
    });
    return groups;
  };

  const productGroups = getProductGroups();

  // Satır arkaplan rengi belirle
  const getRowClassName = (record: ReportData) => {
    const productName = record["Ürün Adı"] || "";
    const productNames = Array.from(new Set(data.map((item) => item["Ürün Adı"]).filter(Boolean))) as string[];
    const groupIndex = productNames.indexOf(productName);
    return groupIndex % 2 === 0 ? "product-group-even" : "product-group-odd";
  };

  // Tablo sütunları
  const columns = [
    {
      title: "Ürün Adı",
      dataIndex: "Ürün Adı",
      key: "Ürün Adı",
      width: 250,
      render: (text: string, record: ReportData) => (
        <div>
          <a href={record["Ürün Linki"]} target="_blank" rel="noopener noreferrer">
            {text}
          </a>
          {record.isBestPrice && <Tag color="gold" style={{ marginLeft: 8 }}>En Ucuz</Tag>}
        </div>
      ),
    },
    {
      title: "Satıcı",
      dataIndex: "Satıcı",
      key: "Satıcı",
      width: 150,
      sorter: (a: ReportData, b: ReportData) => (a["Satıcı"] || "").localeCompare(b["Satıcı"] || ""),
    },
    {
      title: "Orijinal Fiyat",
      dataIndex: "Orijinal Fiyat (TL)",
      key: "Orijinal Fiyat (TL)",
      width: 130,
      render: (price: number) => `₺${price?.toFixed(2) || "N/A"}`,
      sorter: (a: ReportData, b: ReportData) => (a["Orijinal Fiyat (TL)"] || 0) - (b["Orijinal Fiyat (TL)"] || 0),
    },
    {
      title: "Son Fiyat",
      dataIndex: "Son Fiyat (TL)",
      key: "Son Fiyat (TL)",
      width: 130,
      render: (price: number, record: ReportData) => (
        <span style={{ color: record.isBestPrice ? "#faad14" : "inherit", fontWeight: record.isBestPrice ? "bold" : "normal" }}>
          ₺{price?.toFixed(2) || "N/A"}
        </span>
      ),
      sorter: (a: ReportData, b: ReportData) => (a["Son Fiyat (TL)"] || 0) - (b["Son Fiyat (TL)"] || 0),
    },
    {
      title: "Rating",
      dataIndex: "Rating",
      key: "Rating",
      width: 100,
      render: (rating: number) => (
        <span>
          {rating?.toFixed(1) || "N/A"} ⭐
        </span>
      ),
      sorter: (a: ReportData, b: ReportData) => (a["Rating"] || 0) - (b["Rating"] || 0),
    },
    {
      title: "Kupon",
      dataIndex: "Kupon İndirimi",
      key: "Kupon İndirimi",
      width: 150,
      render: (text: string) => text || "-",
    },
    {
      title: "Sepette",
      dataIndex: "Sepette İndirimi",
      key: "Sepette İndirimi",
      width: 150,
      render: (text: string) => text || "-",
    },
  ];

  return (
    <div style={{ padding: "20px" }}>
      <Card>
        <h1>📊 Trendyol Fiyat Raporları</h1>
        <p>GitHub Releases'tan otomatik olarak güncellenen raporlar</p>

        {/* Son Tarama Süresi */}
        <div style={{ marginBottom: 20, padding: "15px", backgroundColor: "#e6f7ff", borderRadius: "8px", border: "1px solid #91d5ff" }}>
          <p style={{ margin: 0, fontSize: "14px", color: "#0050b3" }}>
            <strong>🔄 Son Tarama:</strong> {getLastScanTime()}
          </p>
        </div>

        {/* Kontrol Paneli */}
        <div style={{ marginBottom: 20, padding: "15px", backgroundColor: "#f5f5f5", borderRadius: "8px" }}>
          <Space direction="vertical" style={{ width: "100%" }}>
            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
              <Button 
                type="primary" 
                icon={<ReloadOutlined />} 
                onClick={fetchReport}
                loading={loading}
              >
                Yenile
              </Button>
              <Button 
                type="default" 
                icon={<DownloadOutlined />} 
                onClick={downloadExcel}
              >
                Excel İndir
              </Button>
              <Button 
                type="default" 
                onClick={() => window.location.href = "/trend"}
              >
                Trend Analizi
              </Button>
            </div>

            {/* Filtreleme */}
            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", alignItems: "center" }}>
              <FilterOutlined />
              <Input
                placeholder="Ürün adı veya satıcı ile ara..."
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                style={{ width: "250px" }}
              />
              <Select
                placeholder="Ürün Adı Seç"
                allowClear
                value={selectedProduct || undefined}
                onChange={setSelectedProduct}
                style={{ width: "250px" }}
                options={productNames.map((name) => ({ label: name, value: name }))}
              />
              <Select
                placeholder="Satıcı Seç"
                allowClear
                value={selectedSeller || undefined}
                onChange={setSelectedSeller}
                style={{ width: "200px" }}
                options={sellers.map((seller) => ({ label: seller, value: seller }))}
              />
            </div>
          </Space>
        </div>

        {/* Tablo */}
        <Spin spinning={loading} description="Rapor yükleniyor...">
          {filteredData.length > 0 ? (
            <Table
              columns={columns}
              dataSource={filteredData}
              pagination={{ pageSize: 20, showSizeChanger: true }}
              scroll={{ x: 1200 }}
              size="small"
              rowClassName={(record) => getRowClassName(record)}
            />
          ) : (
            <Empty description="Rapor bulunamadı" />
          )}
        </Spin>
      </Card>
    </div>
  );
}

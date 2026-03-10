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
  const [lastScanTime, setLastScanTime] = useState<string>("");
  const [screenSize, setScreenSize] = useState<'mobile' | 'tablet' | 'web'>('web');

  // Ekran boyutunu takip et
  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      if (width < 768) {
        setScreenSize('mobile');
      } else if (width < 1024) {
        setScreenSize('tablet');
      } else {
        setScreenSize('web');
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Backend'den rapor çek
  const fetchReport = async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/reports/latest");
      if (!response.ok) throw new Error("Rapor yüklenemedi");

      const result = await response.json();
      if (result?.data && Array.isArray(result.data)) {
        // Release tarihi çek
        if (result.releases && result.releases.length > 0) {
          const latestRelease = result.releases[0];
          const releaseDate = new Date(latestRelease.published_at).toLocaleString('tr-TR');
          setLastScanTime(releaseDate);
        }

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
  }, [data, selectedProduct, selectedSeller, searchText]);

  // Ürün adlarını al
  const productNames = Array.from(
    new Set(data.map((item) => item["Ürün Adı"]))
  ).filter(Boolean) as string[];

  // Satıcıları al
  const sellers = Array.from(
    new Set(data.map((item) => item["Satıcı"]))
  ).filter(Boolean) as string[];

  // Son tarama zamanını formatla
  const getLastScanTime = () => {
    return lastScanTime || "Veri yükleniyor...";
  };

  // Ürün gruplaması için row className
  const getRowClassName = (record: ReportData) => {
    const productName = record["Ürün Adı"] || "";
    const productIndex = productNames.indexOf(productName);
    return productIndex % 2 === 0 ? "product-group-even" : "product-group-odd";
  };

  // Excel'e indir
  const downloadExcel = () => {
    const ws = XLSX.utils.json_to_sheet(filteredData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Raporlar");
    XLSX.writeFile(wb, "trendyol-raporlari.xlsx");
  };

  // Responsive tablo sütunları
  const getColumns = () => {
    const baseColumns = [
      {
        title: "Ürün Adı",
        dataIndex: "Ürün Adı",
        key: "Ürün Adı",
        width: screenSize === 'mobile' ? 120 : screenSize === 'tablet' ? 150 : 200,
        render: (text: string) => (
          <a href="#" className="truncate">
            {text}
          </a>
        ),
      },
      {
        title: "Satıcı",
        dataIndex: "Satıcı",
        key: "Satıcı",
        width: screenSize === 'mobile' ? 100 : screenSize === 'tablet' ? 120 : 150,
      },
      {
        title: "Orijinal Fiyat",
        dataIndex: "Orijinal Fiyat (TL)",
        key: "Orijinal Fiyat (TL)",
        width: screenSize === 'mobile' ? 80 : 100,
         render: (price: number) => <span>₺{price?.toFixed(2) || "0"}</span>,
      },
      {
        title: "Son Fiyat",
        dataIndex: "Son Fiyat (TL)",
        key: "Son Fiyat (TL)",
        width: screenSize === 'mobile' ? 80 : 100,
        render: (price: number, record: ReportData) => (
          <span style={{ color: record.isBestPrice ? "#52c41a" : "inherit", fontWeight: record.isBestPrice ? "bold" : "normal" }}>
            ₺{price?.toFixed(2) || "0"}
          </span>
        ),
      },
    ];

    // Tablet ve web için ek sütunlar
    if (screenSize !== 'mobile') {
      baseColumns.push(
        {
          title: "Rating",
          dataIndex: "Rating",
          key: "Rating",
          width: 80,
          render: (rating: number) => <span>{rating} ⭐</span>,
        },
        {
          title: "Kupon",
          dataIndex: "Kupon İndirimi",
          key: "Kupon İndirimi",
          width: 120,
          render: (text: string) => <span>{text || "-"}</span>,
        }
      );
    }

    // Web için tüm sütunlar
    if (screenSize === 'web') {
      baseColumns.push({
        title: "Sepette İndirimi",
        dataIndex: "Sepette İndirimi",
        key: "Sepette İndirimi",
        width: 150,
        render: (text: string) => <span>{text || "-"}</span>,
      });
    }

    return baseColumns;
  };

  return (
    <div className="reports-wrapper">
      <div className="reports-container">
        <Card className="reports-card">
          <div className="reports-header">
            <h1>📊 Trendyol Fiyat Raporları</h1>
            <p>GitHub Releases'tan otomatik olarak güncellenen raporlar</p>
          </div>

          {/* Son Tarama Süresi ve Ürün Sayısı */}
          <div className="scan-info-box">
            <p className="scan-info-item">
              <strong>🔄 Son Tarama:</strong> {getLastScanTime()}
            </p>
            <p className="scan-info-item">
              <strong>📦 Benzersiz Ürün:</strong> {new Set(data.map(item => item["Ürün Adı"])).size} ürün
            </p>
            <p className="scan-info-item">
              <strong>🏪 Toplam Satıcı:</strong> {data.length} kayıt
            </p>
          </div>

          {/* Kontrol Paneli */}
          <div className="controls-panel">
            {/* Buttonlar */}
            <div className="button-group">
              <Button 
                type="primary" 
                icon={<ReloadOutlined />} 
                onClick={fetchReport}
                loading={loading}
                className="control-button"
              >
                Yenile
              </Button>
              <Button 
                type="default" 
                icon={<DownloadOutlined />} 
                onClick={downloadExcel}
                className="control-button"
              >
                Excel İndir
              </Button>
              <Button 
                type="default" 
                onClick={() => window.location.href = "/trend"}
                className="control-button"
              >
                Trend Analizi
              </Button>
            </div>

            {/* Filtreleme */}
            <div className="filter-group">
              <div className="filter-label">
                <FilterOutlined /> Filtrele
              </div>
              <Input
                placeholder="Ürün adı veya satıcı ile ara..."
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                className="filter-input"
              />
              <Select
                placeholder="Ürün Adı Seç"
                allowClear
                value={selectedProduct || undefined}
                onChange={setSelectedProduct}
                className="filter-select"
                options={productNames.map((name) => ({ label: name, value: name }))}
              />
              <Select
                placeholder="Satıcı Seç"
                allowClear
                value={selectedSeller || undefined}
                onChange={setSelectedSeller}
                className="filter-select"
                options={sellers.map((seller) => ({ label: seller, value: seller }))}
              />
            </div>
          </div>

          {/* Tablo */}
          <Spin spinning={loading} description="Rapor yükleniyor...">
            {filteredData.length > 0 ? (
              <Table
                columns={getColumns()}
                dataSource={filteredData}
                pagination={{ 
                  pageSize: screenSize === 'mobile' ? 10 : 20, 
                  showSizeChanger: screenSize !== 'mobile' 
                }}
                scroll={{ x: 'max-content' }}
                size={screenSize === 'mobile' ? 'small' : 'middle'}
                rowClassName={(record) => getRowClassName(record)}
              />
            ) : (
              <Empty description="Rapor bulunamadı" />
            )}
          </Spin>
        </Card>
      </div>
    </div>
  );
}

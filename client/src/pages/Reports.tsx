import { useState, useEffect } from "react";
import { Table, Button, Input, Space, Spin, Empty, message, Card } from "antd";
import { DownloadOutlined, ReloadOutlined } from "@ant-design/icons";
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
}

export default function Reports() {
  const [data, setData] = useState<ReportData[]>([]);
  const [filteredData, setFilteredData] = useState<ReportData[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState("");

  // Backend'den rapor çek
  const fetchReport = async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/reports/latest");
      if (!response.ok) throw new Error("Rapor yüklenemedi");

      const result = await response.json();
      if (result?.data && Array.isArray(result.data)) {
        const dataWithKeys = result.data.map((item: ReportData, index: number) => ({
          ...item,
          key: `${index}`,
        }));
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

  // Arama filtresi
  const handleSearch = (value: string) => {
    setSearchText(value);
    const filtered = data.filter((item) =>
      Object.values(item).some(
        (val) =>
          val &&
          val.toString().toLowerCase().includes(value.toLowerCase())
      )
    );
    setFilteredData(filtered);
  };

  // Excel indir
  const downloadExcel = () => {
    if (data.length === 0) {
      message.warning("İndirilecek veri yok");
      return;
    }

    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Rapor");
    XLSX.writeFile(wb, "trendyol_rapor.xlsx");
    message.success("Excel dosyası indirildi");
  };

  // Tablo sütunları
  const columns = [
    {
      title: "Ürün Adı",
      dataIndex: "Ürün Adı",
      key: "Ürün Adı",
      width: 200,
      render: (text: string) => <span className="truncate">{text}</span>,
    },
    {
      title: "Satıcı",
      dataIndex: "Satıcı",
      key: "Satıcı",
      width: 150,
    },
    {
      title: "Orijinal Fiyat",
      dataIndex: "Orijinal Fiyat (TL)",
      key: "Orijinal Fiyat (TL)",
      width: 120,
      sorter: (a: ReportData, b: ReportData) =>
        (a["Orijinal Fiyat (TL)"] || 0) - (b["Orijinal Fiyat (TL)"] || 0),
      render: (price: number) => `₺${price?.toFixed(2) || "0.00"}`,
    },
    {
      title: "Son Fiyat",
      dataIndex: "Son Fiyat (TL)",
      key: "Son Fiyat (TL)",
      width: 120,
      sorter: (a: ReportData, b: ReportData) =>
        (a["Son Fiyat (TL)"] || 0) - (b["Son Fiyat (TL)"] || 0),
      render: (price: number) => `₺${price?.toFixed(2) || "0.00"}`,
    },
    {
      title: "Rating",
      dataIndex: "Rating",
      key: "Rating",
      width: 100,
      sorter: (a: ReportData, b: ReportData) =>
        (a.Rating || 0) - (b.Rating || 0),
      render: (rating: number) => `${rating?.toFixed(1) || "0.0"} ⭐`,
    },
    {
      title: "Kupon",
      dataIndex: "Kupon İndirimi",
      key: "Kupon İndirimi",
      width: 100,
    },
    {
      title: "Sepette",
      dataIndex: "Sepette İndirimi",
      key: "Sepette İndirimi",
      width: 100,
    },
  ];

  return (
    <div className="reports-container">
      <Card className="reports-card">
        <div className="reports-header">
          <h1>Trendyol Fiyat Raporları</h1>
          <p>GitHub Releases'tan otomatik olarak güncellenen raporlar</p>
        </div>

        <div className="reports-controls">
          <Space>
            <Input
              placeholder="Ürün, satıcı adı ile ara..."
              value={searchText}
              onChange={(e) => handleSearch(e.target.value)}
              style={{ width: 300 }}
            />
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchReport}
              loading={loading}
            >
              Yenile
            </Button>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={downloadExcel}
              disabled={data.length === 0}
            >
              Excel İndir
            </Button>
          </Space>
        </div>

        <Spin spinning={loading} tip="Rapor yükleniyor...">
          {filteredData.length > 0 ? (
            <Table
              columns={columns}
              dataSource={filteredData}
              pagination={{
                pageSize: 20,
                total: filteredData.length,
                showSizeChanger: true,
                showTotal: (total) => `Toplam ${total} ürün`,
              }}
              scroll={{ x: 1200 }}
              size="small"
            />
          ) : (
            <Empty description="Rapor bulunamadı" />
          )}
        </Spin>

        <div className="reports-stats">
          <div className="stat-item">
            <span className="stat-label">Toplam Ürün:</span>
            <span className="stat-value">{data.length}</span>
          </div>
          {data.length > 0 && (
            <>
              <div className="stat-item">
                <span className="stat-label">Ortalama Fiyat:</span>
                <span className="stat-value">
                  ₺
                  {(
                    data.reduce((sum, item) => sum + (item["Son Fiyat (TL)"] || 0), 0) /
                    data.length
                  ).toFixed(2)}
                </span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Min Fiyat:</span>
                <span className="stat-value">
                  ₺
                  {Math.min(
                    ...data.map((item) => item["Son Fiyat (TL)"] || 0)
                  ).toFixed(2)}
                </span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Max Fiyat:</span>
                <span className="stat-value">
                  ₺
                  {Math.max(
                    ...data.map((item) => item["Son Fiyat (TL)"] || 0)
                  ).toFixed(2)}
                </span>
              </div>
            </>
          )}
        </div>
      </Card>
    </div>
  );
}

import { useState, useEffect, useMemo, Fragment } from "react";
import { ChevronDown, ChevronUp, Download, RefreshCw, Filter, ExternalLink, Star, Tag as TagIcon, ShoppingCart } from "lucide-react";
import * as XLSX from "xlsx";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { PriceComparison } from "@/components/PriceComparison";
import "./Reports.css";

const getInitials = (name: string) => {
  const words = name.trim().split(/\s+/);
  if (words.length >= 2)
    return (words[0][0] + words[1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
};

interface ReportData {
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

interface SellerInfo {
  sellerName: string;
  originalPrice: number;
  finalPrice: number;
  rating: number;
  coupon: string;
  cartDiscount: string;
  notes: string;
  isBuyBox: boolean;
}

interface GroupedProduct {
  productName: string;
  productLink: string;
  buyBoxPrice: number;
  buyBoxSeller: string;
  buyBoxRating: number;
  allSellers: SellerInfo[];
}

type SortField = "buyBoxPrice" | "rating" | "sellerCount" | null;
type SortDir = "asc" | "desc";

export default function Reports() {
  const [data, setData] = useState<ReportData[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState("");
  const [selectedProduct, setSelectedProduct] = useState<string>("");
  const [selectedSeller, setSelectedSeller] = useState<string>("");
  const [lastScanTime, setLastScanTime] = useState<string>("");
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [sortField, setSortField] = useState<SortField>(null);
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [selectedRows, setSelectedRows] = useState<Set<string>>(new Set());
  const pageSize = 25;

  // Veriyi ürün bazlı grupla ve Buy Box belirle
  const groupedProducts = useMemo(() => {
    const groups = new Map<string, GroupedProduct>();

    data.forEach((item) => {
      const productName = item["Ürün Adı"] || "";
      const productLink = item["Ürün Linki"] || "";
      
      if (!productName) return;

      const seller: SellerInfo = {
        sellerName: item["Satıcı"] || "",
        originalPrice: item["Orijinal Fiyat (TL)"] || 0,
        finalPrice: item["Son Fiyat (TL)"] || 0,
        rating: item["Rating"] || 0,
        coupon: item["Kupon İndirimi"] || "-",
        cartDiscount: item["Sepette İndirimi"] || "-",
        notes: item["Notlar"] || "",
        isBuyBox: false,
      };

      if (!groups.has(productName)) {
        groups.set(productName, {
          productName,
          productLink,
          buyBoxPrice: seller.finalPrice,
          buyBoxSeller: seller.sellerName,
          buyBoxRating: seller.rating,
          allSellers: [seller],
        });
      } else {
        const group = groups.get(productName)!;
        
        // Aynı satıcı zaten varsa (duplicate kontrolü), ekleme
        const existingSeller = group.allSellers.find(
          s => s.sellerName === seller.sellerName && 
               s.finalPrice === seller.finalPrice
        );
        
        if (!existingSeller) {
          group.allSellers.push(seller);
        }
        
        // En düşük fiyatlı satıcıyı Buy Box olarak belirle
        if (seller.finalPrice < group.buyBoxPrice) {
          group.buyBoxPrice = seller.finalPrice;
          group.buyBoxSeller = seller.sellerName;
          group.buyBoxRating = seller.rating;
        }
      }
    });

    // Her gruptaki Buy Box satıcısını işaretle
    groups.forEach((group) => {
      group.allSellers.forEach((seller) => {
        if (seller.sellerName === group.buyBoxSeller && seller.finalPrice === group.buyBoxPrice) {
          seller.isBuyBox = true;
        }
      });
      // Satıcıları fiyata göre sırala
      group.allSellers.sort((a, b) => a.finalPrice - b.finalPrice);
    });

    return Array.from(groups.values());
  }, [data]);

  // Filtrelenmiş ürünler
  const filteredProducts = useMemo(() => {
    let filtered = groupedProducts;

    // Ürün adı filtresi
    if (selectedProduct && selectedProduct !== "all") {
      filtered = filtered.filter((product) => product.productName === selectedProduct);
    }

    // Satıcı filtresi
    if (selectedSeller && selectedSeller !== "all") {
      filtered = filtered.filter((product) =>
        product.allSellers.some((seller) => seller.sellerName === selectedSeller)
      );
    }

    // Arama filtresi
    if (searchText) {
      const searchLower = searchText.toLowerCase();
      filtered = filtered.filter((product) =>
        product.productName.toLowerCase().includes(searchLower) ||
        product.buyBoxSeller.toLowerCase().includes(searchLower) ||
        product.allSellers.some((seller) =>
          seller.sellerName.toLowerCase().includes(searchLower)
        )
      );
    }

    // Sıralama
    if (sortField) {
      filtered = [...filtered].sort((a, b) => {
        let aVal = 0, bVal = 0;
        if (sortField === "buyBoxPrice") {
          aVal = a.buyBoxPrice; bVal = b.buyBoxPrice;
        } else if (sortField === "rating") {
          aVal = a.buyBoxRating; bVal = b.buyBoxRating;
        } else if (sortField === "sellerCount") {
          aVal = a.allSellers.length; bVal = b.allSellers.length;
        }
        return sortDir === "asc" ? aVal - bVal : bVal - aVal;
      });
    }

    return filtered;
  }, [groupedProducts, selectedProduct, selectedSeller, searchText, sortField, sortDir]);

  // Benzersiz ürün isimleri
  const productNames = useMemo(() => {
    return Array.from(new Set(groupedProducts.map((p) => p.productName))).sort();
  }, [groupedProducts]);

  // Benzersiz satıcılar
  const sellers = useMemo(() => {
    const sellerSet = new Set<string>();
    groupedProducts.forEach((product) => {
      product.allSellers.forEach((seller) => {
        sellerSet.add(seller.sellerName);
      });
    });
    return Array.from(sellerSet).sort();
  }, [groupedProducts]);

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

        setData(result.data);
      }
    } catch (error) {
      console.error("Rapor yüklenirken hata:", error);
    } finally {
      setLoading(false);
    }
  };

  // İlk yüklemede rapor çek
  useEffect(() => {
    fetchReport();
  }, []);

  // Filtreler değişince sayfa 1'e dön
  useEffect(() => {
    setCurrentPage(1);
  }, [filteredProducts.length]);

  // Sayfa değişince accordion kapat
  useEffect(() => {
    setExpandedRow(null);
    setSelectedRows(new Set());
  }, [currentPage, searchText, selectedProduct, selectedSeller]);

  // Sort değişince sayfa 1'e dön ve accordion kapat
  useEffect(() => {
    setCurrentPage(1);
    setExpandedRow(null);
  }, [sortField, sortDir]);

  // Excel'e indir
  const downloadExcel = () => {
    // Düz listeyi export et
    const exportData = filteredProducts.flatMap((product) =>
      product.allSellers.map((seller) => ({
        "Ürün Adı": product.productName,
        "Ürün Linki": product.productLink,
        "Satıcı": seller.sellerName,
        "Orijinal Fiyat (TL)": seller.originalPrice,
        "Kupon İndirimi": seller.coupon,
        "Sepette İndirimi": seller.cartDiscount,
        "Son Fiyat (TL)": seller.finalPrice,
        "Rating": seller.rating,
        "Buy Box": seller.isBuyBox ? "Evet" : "Hayır",
        "Notlar": seller.notes,
      }))
    );

    const ws = XLSX.utils.json_to_sheet(exportData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Raporlar");
    XLSX.writeFile(wb, "trendyol-raporlari.xlsx");
  };

  // Sayfalanmış veri
  const totalPages = Math.ceil(filteredProducts.length / pageSize);
  const paginatedProducts = filteredProducts.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  // Satırı genişlet/daralt
  const toggleRow = (productName: string) => {
    setExpandedRow(prev => prev === productName ? null : productName);
  };

  // Sıralama toggle
  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(prev => prev === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  };

  // Satır seçimi toggle
  const toggleRowSelect = (productName: string) => {
    setSelectedRows(prev => {
      const next = new Set(prev);
      next.has(productName) 
        ? next.delete(productName) 
        : next.add(productName);
      return next;
    });
  };

  // Tümünü seç/seçimi kaldır
  const toggleSelectAll = () => {
    setSelectedRows(prev =>
      prev.size === paginatedProducts.length
        ? new Set()
        : new Set(paginatedProducts.map(p => p.productName))
    );
  };

  // Seçilenleri indir
  const downloadSelected = () => {
    const selected = groupedProducts.filter(p => 
      selectedRows.has(p.productName)
    );
    const exportData = selected.flatMap(product =>
      product.allSellers.map(seller => ({
        "Ürün Adı": product.productName,
        "Ürün Linki": product.productLink,
        "Satıcı": seller.sellerName,
        "Orijinal Fiyat (TL)": seller.originalPrice,
        "Son Fiyat (TL)": seller.finalPrice,
        "İndirim %": Math.round(
          (1 - seller.finalPrice / seller.originalPrice) * 100
        ),
        "Rating": seller.rating,
        "Buy Box": seller.isBuyBox ? "Evet" : "Hayır",
      }))
    );
    const ws = XLSX.utils.json_to_sheet(exportData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Seçilenler");
    XLSX.writeFile(wb, "secilen-urunler.xlsx");
    setSelectedRows(new Set());
  };

  // Sort icon bileşeni
  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return (
      <svg width="12" height="12" viewBox="0 0 24 24" 
        fill="none" stroke="currentColor" 
        strokeWidth="2" className="opacity-30">
        <line x1="12" y1="5" x2="12" y2="19"/>
        <polyline points="19 12 12 19 5 12"/>
      </svg>
    );
    return sortDir === "asc" ? (
      <ChevronUp className="h-3 w-3 text-emerald-600" />
    ) : (
      <ChevronDown className="h-3 w-3 text-emerald-600" />
    );
  };

  return (
    <div className="reports-wrapper p-4 md:p-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span className="text-2xl">📊</span>
            Trendyol Fiyat Raporları
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* İstatistikler */}
          <div className="border rounded-xl overflow-hidden grid grid-cols-3">
            
            <div className="flex items-center gap-3 px-6 py-4 border-r">
              <div className="w-2 h-2 rounded-full bg-orange-400 shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground mb-0.5">Son Tarama</p>
                <p className="text-sm font-medium">
                  {lastScanTime || "—"}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 px-6 py-4 border-r">
              <div className="w-2 h-2 rounded-full bg-blue-400 shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground mb-0.5">Toplam Ürün</p>
                <p className="text-sm font-medium">{groupedProducts.length} ürün</p>
              </div>
            </div>

            <div className="flex items-center gap-3 px-6 py-4">
              <div className="w-2 h-2 rounded-full bg-emerald-400 shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground mb-0.5">Satıcı Kaydı</p>
                <p className="text-sm font-medium">{data.length} kayıt</p>
              </div>
            </div>

          </div>

          {/* Kontrol Paneli */}
          <div className="flex flex-col gap-4">
            {/* Buttonlar */}
            <div className="flex flex-wrap gap-2">
              <Button onClick={fetchReport} disabled={loading}>
                <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                Yenile
              </Button>
              <Button variant="outline" onClick={downloadExcel}>
                <Download className="mr-2 h-4 w-4" />
                Excel İndir
              </Button>
              <Button variant="outline" onClick={() => window.location.href = "/trend"}>
                Trend Analizi
              </Button>
            </div>

            {/* Filtreler */}
            <div className="flex flex-col md:flex-row gap-2">
              <div className="flex-1">
                <Input
                  placeholder="Ürün adı veya satıcı ile ara..."
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                  className="w-full"
                />
              </div>
              <Select value={selectedProduct || "all"} onValueChange={(val) => setSelectedProduct(val === "all" ? "" : val)}>
                <SelectTrigger className="w-full md:w-[200px]">
                  <SelectValue placeholder="Tüm Ürünler" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tüm Ürünler</SelectItem>
                  {productNames.map((name) => (
                    <SelectItem key={name} value={name}>
                      {name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={selectedSeller || "all"} onValueChange={(val) => setSelectedSeller(val === "all" ? "" : val)}>
                <SelectTrigger className="w-full md:w-[200px]">
                  <SelectValue placeholder="Tüm Satıcılar" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tüm Satıcılar</SelectItem>
                  {sellers.map((seller) => (
                    <SelectItem key={seller} value={seller}>
                      {seller}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Aktif Filtre Pill'leri */}
            {(searchText || selectedProduct || selectedSeller) && (
              <div className="flex items-center gap-2 flex-wrap pt-1">
                <span className="text-xs text-muted-foreground">
                  Aktif filtreler:
                </span>

                {searchText && (
                  <button
                    onClick={() => setSearchText("")}
                    className="inline-flex items-center gap-1.5 
                      bg-blue-50 text-blue-700 border border-blue-200
                      text-[11px] font-medium px-2.5 py-1 rounded-full
                      hover:bg-blue-100 transition-colors"
                  >
                    <svg width="10" height="10" viewBox="0 0 24 24" 
                      fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="11" cy="11" r="8"/>
                      <path d="M21 21l-4.35-4.35"/>
                    </svg>
                    "{searchText}"
                    <svg width="10" height="10" viewBox="0 0 24 24" 
                      fill="none" stroke="currentColor" strokeWidth="2.5">
                      <line x1="18" y1="6" x2="6" y2="18"/>
                      <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                  </button>
                )}

                {selectedProduct && (
                  <button
                    onClick={() => setSelectedProduct("")}
                    className="inline-flex items-center gap-1.5
                      bg-emerald-50 text-emerald-700 border border-emerald-200
                      text-[11px] font-medium px-2.5 py-1 rounded-full
                      hover:bg-emerald-100 transition-colors"
                  >
                    <svg width="10" height="10" viewBox="0 0 24 24"
                      fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="2" y="3" width="20" height="14" rx="2"/>
                      <path d="M8 21h8M12 17v4"/>
                    </svg>
                    {selectedProduct.length > 30 
                      ? selectedProduct.slice(0, 30) + "..." 
                      : selectedProduct}
                    <svg width="10" height="10" viewBox="0 0 24 24"
                      fill="none" stroke="currentColor" strokeWidth="2.5">
                      <line x1="18" y1="6" x2="6" y2="18"/>
                      <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                  </button>
                )}

                {selectedSeller && (
                  <button
                    onClick={() => setSelectedSeller("")}
                    className="inline-flex items-center gap-1.5
                      bg-amber-50 text-amber-700 border border-amber-200
                      text-[11px] font-medium px-2.5 py-1 rounded-full
                      hover:bg-amber-100 transition-colors"
                  >
                    <svg width="10" height="10" viewBox="0 0 24 24"
                      fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                      <circle cx="9" cy="7" r="4"/>
                    </svg>
                    {selectedSeller}
                    <svg width="10" height="10" viewBox="0 0 24 24"
                      fill="none" stroke="currentColor" strokeWidth="2.5">
                      <line x1="18" y1="6" x2="6" y2="18"/>
                      <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                  </button>
                )}

                {(searchText && selectedProduct) || 
                 (searchText && selectedSeller) || 
                 (selectedProduct && selectedSeller) ? (
                  <button
                    onClick={() => {
                      setSearchText("")
                      setSelectedProduct("")
                      setSelectedSeller("")
                    }}
                    className="inline-flex items-center gap-1
                      text-[11px] text-muted-foreground
                      hover:text-foreground transition-colors
                      underline underline-offset-2"
                  >
                    Tümünü temizle
                  </button>
                ) : null}
              </div>
            )}

            {/* Seçim Aksiyon Barı */}
            {selectedRows.size > 0 && (
              <div className="flex items-center justify-between
                bg-emerald-50 border border-emerald-200 
                rounded-lg px-4 py-2.5">
                <span className="text-sm font-medium text-emerald-700">
                  {selectedRows.size} ürün seçildi
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setSelectedRows(new Set())}
                    className="text-xs text-emerald-600 
                      hover:text-emerald-800 transition-colors"
                  >
                    Seçimi temizle
                  </button>
                  <button
                    onClick={downloadSelected}
                    className="inline-flex items-center gap-1.5
                      bg-emerald-600 text-white text-xs font-medium
                      px-3 py-1.5 rounded-md
                      hover:bg-emerald-700 transition-colors"
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24"
                      fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                      <polyline points="7 10 12 15 17 10"/>
                      <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    Seçilenleri İndir
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Tablo */}
          {loading ? (
            <div className="flex justify-center items-center py-12">
              <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
              <span className="ml-2 text-muted-foreground">Rapor yükleniyor...</span>
            </div>
          ) : filteredProducts.length === 0 ? (
            <div className="flex flex-col items-center justify-center 
              py-16 gap-4">
              
              <div className="w-12 h-12 rounded-full bg-muted 
                flex items-center justify-center">
                <svg width="20" height="20" viewBox="0 0 24 24" 
                  fill="none" stroke="currentColor" 
                  strokeWidth="1.5" className="text-muted-foreground">
                  <circle cx="11" cy="11" r="8"/>
                  <path d="M21 21l-4.35-4.35"/>
                </svg>
              </div>

              <div className="text-center">
                <p className="text-sm font-medium text-foreground mb-1">
                  {searchText 
                    ? `"${searchText}" için sonuç bulunamadı`
                    : selectedProduct || selectedSeller
                      ? "Seçili filtreye uyan ürün bulunamadı"
                      : "Henüz rapor verisi yok"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {searchText || selectedProduct || selectedSeller
                    ? "Farklı bir arama deneyin veya filtreyi kaldırın"
                    : "Yenile butonuna tıklayarak veri çekmeyi deneyin"}
                </p>
              </div>

              {(searchText || selectedProduct || selectedSeller) && (
                <button
                  onClick={() => {
                    setSearchText("")
                    setSelectedProduct("")
                    setSelectedSeller("")
                  }}
                  className="inline-flex items-center gap-2 
                    text-sm text-muted-foreground border 
                    border-border rounded-lg px-4 py-2
                    hover:bg-muted hover:text-foreground 
                    transition-colors"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24"
                    fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                  Filtreyi temizle
                </button>
              )}

              {!searchText && !selectedProduct && !selectedSeller && (
                <button
                  onClick={fetchReport}
                  className="inline-flex items-center gap-2
                    text-sm text-muted-foreground border
                    border-border rounded-lg px-4 py-2
                    hover:bg-muted hover:text-foreground
                    transition-colors"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24"
                    fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M1 4v6h6"/>
                    <path d="M23 20v-6h-6"/>
                    <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10
                         m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/>
                  </svg>
                  Yenile
                </button>
              )}

            </div>
          ) : (
            <div className="border rounded-lg overflow-hidden overflow-x-auto relative">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10">
                      <input
                        type="checkbox"
                        className="rounded border-border cursor-pointer"
                        checked={selectedRows.size === paginatedProducts.length 
                                 && paginatedProducts.length > 0}
                        onChange={toggleSelectAll}
                      />
                    </TableHead>
                    <TableHead className="w-12 px-4"></TableHead>
                    <TableHead className="text-left px-4">Ürün Adı</TableHead>
                    <TableHead 
                      className="text-right px-4 cursor-pointer select-none hover:text-foreground transition-colors"
                      onClick={() => toggleSort("buyBoxPrice")}
                    >
                      <div className="flex items-center justify-end gap-1">
                        Buy Box Fiyat <SortIcon field="buyBoxPrice" />
                      </div>
                    </TableHead>
                    <TableHead className="text-left px-4 w-[150px]">Buy Box Satıcı</TableHead>
                    <TableHead 
                      className="hidden md:table-cell text-center px-4 cursor-pointer select-none hover:text-foreground transition-colors"
                      onClick={() => toggleSort("rating")}
                    >
                      <div className="flex items-center justify-center gap-1">
                        Rating <SortIcon field="rating" />
                      </div>
                    </TableHead>
                    <TableHead 
                      className="text-center px-4 cursor-pointer select-none hover:text-foreground transition-colors"
                      onClick={() => toggleSort("sellerCount")}
                    >
                      <div className="flex items-center justify-center gap-1">
                        Satıcı Sayısı <SortIcon field="sellerCount" />
                      </div>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedProducts.map((product) => {
                    const isExpanded = expandedRow === product.productName;
                    const hasMultipleSellers = product.allSellers.length > 1;
                    
                    return (
                      <Fragment key={product.productName}>
                        <TableRow
                          onClick={() => {
                            if (hasMultipleSellers) {
                              toggleRow(product.productName);
                            }
                          }}
                          className={`transition-all duration-200 ${
                              hasMultipleSellers ? "cursor-pointer" : ""
                            } ${
                              isExpanded
                                ? "bg-muted/60 border-l-2 border-l-emerald-500"
                                : expandedRow !== null
                                  ? "opacity-35 pointer-events-none"
                                  : hasMultipleSellers
                                    ? "hover:bg-muted/30"
                                    : ""
                            }`}
                          >
                            <TableCell className="w-10 px-4" onClick={e => e.stopPropagation()}>
                              <input
                                type="checkbox"
                                className="rounded border-border cursor-pointer"
                                checked={selectedRows.has(product.productName)}
                                onChange={() => toggleRowSelect(product.productName)}
                              />
                            </TableCell>
                            <TableCell className="w-9 px-4">
                              {hasMultipleSellers ? (
                                isExpanded 
                                  ? <ChevronUp className="h-4 w-4 text-muted-foreground" />
                                  : <ChevronDown className="h-4 w-4 text-muted-foreground" />
                              ) : (
                                <div className="w-4" />
                              )}
                            </TableCell>
                            <TableCell className="min-w-0 max-w-0 px-4">
                              <div className="flex items-center gap-2 min-w-0">
                                <TooltipProvider delayDuration={300}>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <span className="truncate max-w-[420px] block font-medium">
                                        {product.productName}
                                      </span>
                                    </TooltipTrigger>
                                    <TooltipContent
                                      side="top"
                                      className="max-w-[420px] text-xs leading-relaxed"
                                    >
                                      {product.productName}
                                    </TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                                {product.productLink && (
                                  <a
                                    href={product.productLink}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    onClick={(e) => e.stopPropagation()}
                                    className="text-blue-600 hover:text-blue-800"
                                  >
                                    <ExternalLink className="h-4 w-4" />
                                  </a>
                                )}
                              </div>
                            </TableCell>
                            <TableCell className="text-right px-4 font-semibold text-green-600 text-base">
                              ₺{product.buyBoxPrice.toFixed(2)}
                            </TableCell>
                            <TableCell className="px-4">
                              <TooltipProvider delayDuration={300}>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Badge className="bg-green-600 text-white max-w-[120px] truncate block text-center">
                                      {product.buyBoxSeller}
                                    </Badge>
                                  </TooltipTrigger>
                                  <TooltipContent side="top" className="text-xs">
                                    {product.buyBoxSeller}
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            </TableCell>
                            <TableCell className="hidden md:table-cell text-center px-4">
                              <div className="flex items-center justify-center gap-1">
                                <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                                <span>{product.buyBoxRating}</span>
                              </div>
                            </TableCell>
                            <TableCell className="text-center px-4">
                              <div className="inline-flex items-center justify-center gap-1">
                                <span className="font-medium tabular-nums">{product.allSellers.length}</span>
                                {product.allSellers.length > 1 && (
                                  <ChevronDown className={`h-3 w-3 text-muted-foreground 
                                    transition-transform duration-200 ${
                                      isExpanded ? "rotate-180" : ""
                                    }`}
                                  />
                                )}
                              </div>
                            </TableCell>
                          </TableRow>
                        {isExpanded && (
                          <TableRow className="border-l-2 border-l-emerald-500">
                            <TableCell
                              colSpan={7}
                              className="p-0 bg-muted/20 animate-in fade-in-0 slide-in-from-top-1 duration-200"
                            >
                                <div className="p-4">
                                  <div className="flex flex-col gap-2">
                                    {product.allSellers
                                      .sort((a, b) => a.finalPrice - b.finalPrice)
                                      .map((seller, idx) => {
                                        const discount = Math.round((1 - seller.finalPrice / seller.originalPrice) * 100);
                                        const initials = getInitials(seller.sellerName);
                                        
                                        return (
                                          <div
                                            key={idx}
                                            className={`bg-white border rounded-xl p-4 grid grid-cols-4 gap-4 items-center transition-all duration-150 ${
                                              seller.isBuyBox 
                                                ? 'border-emerald-300 bg-emerald-50/50 hover:border-emerald-400 hover:shadow-sm' 
                                                : 'hover:border-border hover:shadow-sm'
                                            }`}
                                          >
                                            {/* Satıcı Kimliği */}
                                            <div className="w-44 flex items-center gap-3">
                                              <div
                                                className={`w-9 h-9 rounded-full flex items-center justify-center text-[11px] font-semibold ${
                                                  seller.isBuyBox
                                                    ? 'bg-emerald-500 text-white'
                                                    : 'bg-muted text-muted-foreground'
                                                }`}
                                              >
                                                {initials}
                                              </div>
                                              <div className="flex flex-col">
                                                <TooltipProvider delayDuration={300}>
                                                  <Tooltip>
                                                    <TooltipTrigger asChild>
                                                      <span className="font-medium text-sm truncate max-w-[140px] block">
                                                        {seller.sellerName}
                                                      </span>
                                                    </TooltipTrigger>
                                                    <TooltipContent side="top" className="text-xs">
                                                      {seller.sellerName}
                                                    </TooltipContent>
                                                  </Tooltip>
                                                </TooltipProvider>
                                                {seller.isBuyBox && (
                                                  <span className="bg-emerald-500 text-white text-[10px] rounded-full px-2 py-0.5 w-fit mt-0.5">
                                                    Buy Box
                                                  </span>
                                                )}
                                              </div>
                                            </div>

                                            {/* Fiyat Grubu */}
                                            <div className="flex items-center gap-2">
                                              <span className="line-through text-muted-foreground text-sm">
                                                ₺{seller.originalPrice.toFixed(2)}
                                              </span>
                                              <span className="text-muted-foreground">→</span>
                                              <span className="font-semibold text-base">
                                                ₺{seller.finalPrice.toFixed(2)}
                                              </span>
                                              {discount > 0 && seller.originalPrice !== seller.finalPrice && (
                                                <span className="bg-emerald-50 text-emerald-700 text-[11px] rounded-full px-2 py-0.5">
                                                  %{discount}
                                                </span>
                                              )}
                                            </div>

                                            {/* Etiketler */}
                                            <div className="flex gap-1.5 flex-wrap">
                                              {seller.coupon !== "-" && (
                                                <div className="border rounded-md px-2 py-0.5 text-[11px] text-muted-foreground flex items-center gap-1">
                                                  <TagIcon className="h-3 w-3" />
                                                  {seller.coupon}
                                                </div>
                                              )}
                                              {seller.cartDiscount !== "-" && (
                                                <div className="border rounded-md px-2 py-0.5 text-[11px] text-muted-foreground flex items-center gap-1">
                                                  <ShoppingCart className="h-3 w-3" />
                                                  {seller.cartDiscount}
                                                </div>
                                              )}
                                            </div>

                                            {/* Rating */}
                                            <div className="text-right flex items-center justify-end gap-1">
                                              <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                                              <span className="text-sm">{seller.rating}</span>
                                            </div>
                                          </div>
                                        );
                                      })}
                                  </div>
                                </div>
                              </TableCell>
                            </TableRow>
                          )}
                      </Fragment>
                    );
                  })}
                </TableBody>
              </Table>
              <div className="flex items-center justify-between px-2 py-3 border-t">
                <span className="text-sm text-muted-foreground">
                  {filteredProducts.length} üründen {(currentPage - 1) * pageSize + 1}–{Math.min(currentPage * pageSize, filteredProducts.length)} gösteriliyor
                </span>
                <div className="flex items-center gap-1">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={currentPage === 1}
                    onClick={() => setCurrentPage(p => p - 1)}
                  >
                    ← Önceki
                  </Button>
                  {Array.from({ length: totalPages }, (_, i) => i + 1)
                    .filter(p => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 1)
                    .reduce((acc, p, i, arr) => {
                      if (i > 0 && p - arr[i - 1] > 1) {
                        acc.push(
                          <span key={'e' + p} className="px-1 text-muted-foreground">
                            …
                          </span>
                        );
                      }
                      acc.push(
                        <Button
                          key={p}
                          variant={p === currentPage ? "default" : "outline"}
                          size="sm"
                          onClick={() => setCurrentPage(p)}
                        >
                          {p}
                        </Button>
                      );
                      return acc;
                    }, [] as React.ReactNode[])}
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={currentPage === totalPages}
                    onClick={() => setCurrentPage(p => p + 1)}
                  >
                    Sonraki →
                  </Button>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

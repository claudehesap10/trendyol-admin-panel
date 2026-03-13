import { useState, useEffect, useMemo, Fragment } from "react";
import { ChevronDown, ChevronUp, Download, RefreshCw, ExternalLink, Star, Tag as TagIcon, ShoppingCart, X } from "lucide-react";
import * as XLSX from "xlsx";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import "./Reports.css";

const getInitials = (name: string) => {
  const words = name.trim().split(/\s+/);
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
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
type QuickFilter = 'won' | 'lost' | 'risky' | 'alone' | 'multi' | null;

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
  const [quickFilter, setQuickFilter] = useState<QuickFilter>(null);
  const [mySellerName, setMySellerName] = useState("Esvento");
  const pageSize = 25;

  // ─── Gruplama: Buy Box = en ucuz satıcı ──────────────────────────────────
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
        groups.set(productName, { productName, productLink, buyBoxPrice: 0, buyBoxSeller: "", buyBoxRating: 0, allSellers: [seller] });
      } else {
        const group = groups.get(productName)!;
        const exists = group.allSellers.find(s => s.sellerName === seller.sellerName && s.finalPrice === seller.finalPrice);
        if (!exists) group.allSellers.push(seller);
      }
    });
    groups.forEach((group) => {
      group.allSellers.sort((a, b) => a.finalPrice - b.finalPrice);
      group.allSellers.forEach((s, i) => { s.isBuyBox = i === 0; });
      const winner = group.allSellers[0];
      group.buyBoxPrice = winner.finalPrice;
      group.buyBoxSeller = winner.sellerName;
      group.buyBoxRating = winner.rating;
    });
    return Array.from(groups.values());
  }, [data]);

  // ─── İstatistikler ────────────────────────────────────────────────────────
  const buyBoxStats = useMemo(() => {
    let buyBoxMine = 0, buyBoxLost = 0, buyBoxRisky = 0, notMySeller = 0;
    const myName = mySellerName.trim().toLowerCase();
    groupedProducts.forEach(product => {
      const myData = product.allSellers.find(s => s.sellerName.trim().toLowerCase() === myName);
      if (!myData) { notMySeller++; return; }
      const iAmCheapest = product.allSellers[0].sellerName.trim().toLowerCase() === myName;
      if (iAmCheapest) {
        const cheapestRival = product.allSellers.find(s => s.sellerName.trim().toLowerCase() !== myName);
        const gap = cheapestRival ? cheapestRival.finalPrice - myData.finalPrice : Infinity;
        if (gap < 50) buyBoxRisky++; else buyBoxMine++;
      } else { buyBoxLost++; }
    });
    return { buyBoxMine, buyBoxLost, buyBoxRisky, notMySeller };
  }, [groupedProducts, mySellerName]);

  // ─── Filtreleme ───────────────────────────────────────────────────────────
  const filteredProducts = useMemo(() => {
    const myName = mySellerName.trim().toLowerCase();
    let filtered = groupedProducts;
    if (selectedProduct && selectedProduct !== "all")
      filtered = filtered.filter(p => p.productName === selectedProduct);
    if (selectedSeller && selectedSeller !== "all")
      filtered = filtered.filter(p => p.allSellers.some(s => s.sellerName === selectedSeller));
    if (searchText) {
      const q = searchText.toLowerCase();
      filtered = filtered.filter(p =>
        p.productName.toLowerCase().includes(q) ||
        p.allSellers.some(s => s.sellerName.toLowerCase().includes(q))
      );
    }
    if (quickFilter === 'won') {
      // Buy Box kazandıklarım: En ucuz benim (riskli olanlar dahil)
      filtered = filtered.filter(product => {
        const myData = product.allSellers.find(s => s.sellerName.toLowerCase() === myName);
        if (!myData) return false;
        return product.allSellers[0].sellerName.toLowerCase() === myName;
      });
    } else if (quickFilter === 'lost') {
      filtered = filtered.filter(product => {
        const myData = product.allSellers.find(s => s.sellerName.toLowerCase() === myName);
        if (!myData) return false;
        return product.allSellers[0].sellerName.toLowerCase() !== myName;
      });
    } else if (quickFilter === 'risky') {
      filtered = filtered.filter(product => {
        const myData = product.allSellers.find(s => s.sellerName.toLowerCase() === myName);
        if (!myData) return false;
        if (product.allSellers[0].sellerName.toLowerCase() !== myName) return false;
        const cheapestRival = product.allSellers.find(s => s.sellerName.toLowerCase() !== myName);
        return cheapestRival && (cheapestRival.finalPrice - myData.finalPrice) < 50;
      });
    } else if (quickFilter === 'alone') {
      filtered = filtered.filter(product => {
        const iAmSeller = product.allSellers.some(s => s.sellerName.toLowerCase() === myName);
        return iAmSeller && product.allSellers.length === 1;
      });
    } else if (quickFilter === 'multi') {
      filtered = filtered.filter(p => p.allSellers.length >= 3);
    }
    if (sortField) {
      filtered = [...filtered].sort((a, b) => {
        let aVal = 0, bVal = 0;
        if (sortField === "buyBoxPrice") { aVal = a.buyBoxPrice; bVal = b.buyBoxPrice; }
        else if (sortField === "rating") { aVal = a.buyBoxRating; bVal = b.buyBoxRating; }
        else if (sortField === "sellerCount") { aVal = a.allSellers.length; bVal = b.allSellers.length; }
        return sortDir === "asc" ? aVal - bVal : bVal - aVal;
      });
    }
    return filtered;
  }, [groupedProducts, selectedProduct, selectedSeller, searchText, sortField, sortDir, quickFilter, mySellerName]);

  const productNames = useMemo(() => Array.from(new Set(groupedProducts.map(p => p.productName))).sort(), [groupedProducts]);
  const sellers = useMemo(() => {
    const s = new Set<string>();
    groupedProducts.forEach(p => p.allSellers.forEach(sel => s.add(sel.sellerName)));
    return Array.from(s).sort();
  }, [groupedProducts]);

  const fetchReport = async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/reports/latest");
      if (!response.ok) throw new Error("Rapor yüklenemedi");
      const result = await response.json();
      if (result?.data && Array.isArray(result.data)) {
        if (result.releases?.length > 0)
          setLastScanTime(new Date(result.releases[0].published_at).toLocaleString('tr-TR'));
        setData(result.data);
      }
    } catch (error) { console.error("Rapor yüklenirken hata:", error); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchReport(); }, []);
  useEffect(() => { setCurrentPage(1); }, [filteredProducts.length]);
  useEffect(() => { setExpandedRow(null); setSelectedRows(new Set()); }, [currentPage, searchText, selectedProduct, selectedSeller]);
  useEffect(() => { setCurrentPage(1); setExpandedRow(null); }, [sortField, sortDir, quickFilter]);

  const downloadExcel = () => {
    const exportData = filteredProducts.flatMap(product =>
      product.allSellers.map(seller => ({
        "Ürün Adı": product.productName, "Ürün Linki": product.productLink,
        "Satıcı": seller.sellerName, "Orijinal Fiyat (TL)": seller.originalPrice,
        "Kupon İndirimi": seller.coupon, "Sepette İndirimi": seller.cartDiscount,
        "Son Fiyat (TL)": seller.finalPrice, "Rating": seller.rating,
        "Buy Box": seller.isBuyBox ? "Evet" : "Hayır", "Notlar": seller.notes,
      }))
    );
    const ws = XLSX.utils.json_to_sheet(exportData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Raporlar");
    XLSX.writeFile(wb, "trendyol-raporlari.xlsx");
  };

  const downloadSelected = () => {
    const selected = groupedProducts.filter(p => selectedRows.has(p.productName));
    const exportData = selected.flatMap(product =>
      product.allSellers.map(seller => ({
        "Ürün Adı": product.productName, "Ürün Linki": product.productLink,
        "Satıcı": seller.sellerName, "Orijinal Fiyat (TL)": seller.originalPrice,
        "Son Fiyat (TL)": seller.finalPrice,
        "İndirim %": Math.round((1 - seller.finalPrice / seller.originalPrice) * 100),
        "Rating": seller.rating, "Buy Box": seller.isBuyBox ? "Evet" : "Hayır",
      }))
    );
    const ws = XLSX.utils.json_to_sheet(exportData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Seçilenler");
    XLSX.writeFile(wb, "secilen-urunler.xlsx");
    setSelectedRows(new Set());
  };

  const totalPages = Math.ceil(filteredProducts.length / pageSize);
  const paginatedProducts = filteredProducts.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const toggleRow = (name: string) => setExpandedRow(prev => prev === name ? null : name);
  const toggleSort = (field: SortField) => {
    if (sortField === field) setSortDir(prev => prev === "asc" ? "desc" : "asc");
    else { setSortField(field); setSortDir("asc"); }
  };
  const toggleRowSelect = (name: string) => {
    setSelectedRows(prev => { const next = new Set(prev); next.has(name) ? next.delete(name) : next.add(name); return next; });
  };
  const toggleSelectAll = () => {
    setSelectedRows(prev => prev.size === paginatedProducts.length ? new Set() : new Set(paginatedProducts.map(p => p.productName)));
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="opacity-30"><line x1="12" y1="5" x2="12" y2="19" /><polyline points="19 12 12 19 5 12" /></svg>;
    return sortDir === "asc" ? <ChevronUp className="h-3 w-3 text-emerald-600" /> : <ChevronDown className="h-3 w-3 text-emerald-600" />;
  };

  const myName = mySellerName.trim().toLowerCase();

  // Hızlı filtre tanımları
  const quickFilters = [
    {
      id: 'won' as QuickFilter,
      label: 'Buy Box kazandıklarım',
      count: buyBoxStats.buyBoxMine + buyBoxStats.buyBoxRisky, // riskli olanlar da kazanılanlar içinde
      activeColor: 'bg-emerald-500 border-emerald-500',
      hoverColor: 'hover:border-emerald-300 hover:text-emerald-600',
      countBg: 'bg-emerald-100 text-emerald-700',
      activeCountBg: 'bg-emerald-400 text-white',
      icon: <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12" /></svg>,
    },
    {
      id: 'lost' as QuickFilter,
      label: 'Buy Box kaybettiklerim',
      count: buyBoxStats.buyBoxLost,
      activeColor: 'bg-red-500 border-red-500',
      hoverColor: 'hover:border-red-300 hover:text-red-600',
      countBg: 'bg-red-100 text-red-700',
      activeCountBg: 'bg-red-400 text-white',
      icon: <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>,
    },
    {
      id: 'risky' as QuickFilter,
      label: 'Riskli (<50₺)',
      count: buyBoxStats.buyBoxRisky,
      activeColor: 'bg-amber-500 border-amber-500',
      hoverColor: 'hover:border-amber-300 hover:text-amber-600',
      countBg: 'bg-amber-100 text-amber-700',
      activeCountBg: 'bg-amber-400 text-white',
      icon: <span className="text-[11px]">⚠️</span>,
    },
    {
      id: 'alone' as QuickFilter,
      label: 'Tek satıcıyım',
      count: null,
      activeColor: 'bg-blue-500 border-blue-500',
      hoverColor: 'hover:border-blue-300 hover:text-blue-600',
      countBg: '',
      activeCountBg: '',
      icon: <span className="text-[11px]">🟢</span>,
    },
    {
      id: 'multi' as QuickFilter,
      label: '3+ satıcılı',
      count: null,
      activeColor: 'bg-purple-500 border-purple-500',
      hoverColor: 'hover:border-purple-300 hover:text-purple-600',
      countBg: '',
      activeCountBg: '',
      icon: <span className="text-[11px]">🔥</span>,
    },
  ];

  return (
    <div className="reports-wrapper p-3 md:p-6">
      <Card>
        <CardHeader className="pb-3 px-4 md:px-6">
          <CardTitle className="flex items-center gap-2 text-lg md:text-2xl">
            <span>📊</span>
            Trendyol Fiyat Raporları
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-4 px-3 md:px-6">

          {/* ══ İSTATİSTİK KARTLARI ══════════════════════════════════════════ */}
          <div className="flex flex-col gap-3 md:grid md:grid-cols-4">

            {/* Buy Box Durumu */}
            <div className="md:col-span-1 border rounded-xl p-4 bg-emerald-50 border-emerald-200">
              <p className="text-xs text-emerald-700 font-medium mb-2.5">Buy Box Durumu</p>
              {/* Mobilde yatay, masaüstünde dikey */}
              <div className="flex flex-row flex-wrap gap-x-4 gap-y-2 md:flex-col">
                <div className="flex items-center gap-1.5">
                  <div className="w-4 h-4 rounded-full bg-emerald-500 flex items-center justify-center shrink-0">
                    <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3"><polyline points="20 6 9 17 4 12" /></svg>
                  </div>
                  <span className="text-xs text-emerald-700">Kazandım:</span>
                  <span className="text-sm font-bold text-emerald-700">{buyBoxStats.buyBoxMine}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-sm leading-none">⚠️</span>
                  <span className="text-xs text-amber-700">Riskli:</span>
                  <span className="text-sm font-bold text-amber-700">{buyBoxStats.buyBoxRisky}</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-4 h-4 rounded-full bg-red-500 flex items-center justify-center shrink-0">
                    <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
                  </div>
                  <span className="text-xs text-red-700">Kaybettim:</span>
                  <span className="text-sm font-bold text-red-700">{buyBoxStats.buyBoxLost}</span>
                </div>
              </div>
            </div>

            {/* 3 bilgi kutusu */}
            <div className="md:col-span-3 border rounded-xl overflow-hidden grid grid-cols-3">
              {[
                { dot: 'bg-orange-400', label: 'Son Tarama', value: lastScanTime || '—', sub: null },
                { dot: 'bg-blue-400', label: 'Toplam Ürün', value: `${groupedProducts.length}`, sub: buyBoxStats.notMySeller > 0 ? `${buyBoxStats.notMySeller} takip` : null },
                { dot: 'bg-emerald-400', label: 'Satıcı Kaydı', value: `${data.length}`, sub: null },
              ].map((item, i) => (
                <div key={i} className={`flex items-center gap-2 px-3 sm:px-5 py-3 sm:py-4 ${i < 2 ? 'border-r' : ''}`}>
                  <div className={`w-1.5 h-1.5 rounded-full ${item.dot} shrink-0 hidden sm:block`} />
                  <div className="min-w-0">
                    <p className="text-[10px] sm:text-xs text-muted-foreground mb-0.5 whitespace-nowrap">{item.label}</p>
                    <p className="text-xs sm:text-sm font-medium leading-tight truncate">{item.value}</p>
                    {item.sub && <p className="text-[9px] sm:text-[10px] text-muted-foreground">{item.sub}</p>}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ══ KONTROL PANELİ ════════════════════════════════════════════════ */}
          <div className="flex flex-col gap-3">

            {/* Butonlar satırı */}
            <div className="flex flex-wrap items-center gap-2">
              <Button onClick={fetchReport} disabled={loading} size="sm" className="h-8">
                <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
                <span className="text-xs">Yenile</span>
              </Button>
              <Button variant="outline" onClick={downloadExcel} size="sm" className="h-8">
                <Download className="mr-1.5 h-3.5 w-3.5" />
                <span className="text-xs hidden sm:inline">Excel İndir</span>
                <span className="text-xs sm:hidden">Excel</span>
              </Button>
              <Button variant="outline" onClick={() => window.location.href = "/trend"} size="sm" className="h-8">
                <span className="text-xs hidden sm:inline">Trend Analizi</span>
                <span className="text-xs sm:hidden">Trend</span>
              </Button>
              {/* Satıcı adı — mobilde tam satır */}
              <div className="flex items-center gap-2 w-full sm:w-auto sm:ml-auto mt-1 sm:mt-0">
                <span className="text-xs text-muted-foreground whitespace-nowrap">Satıcım:</span>
                <Input
                  value={mySellerName}
                  onChange={e => setMySellerName(e.target.value)}
                  className="h-8 flex-1 sm:w-36 text-xs"
                  placeholder="Satıcı adın..."
                />
              </div>
            </div>

            {/* Hızlı Filtreler — yatay scroll */}
            <div className="flex gap-2 overflow-x-auto pb-0.5 -mx-1 px-1" style={{ scrollbarWidth: 'none' }}>
              {quickFilters.map(f => (
                <button
                  key={f.id}
                  onClick={() => setQuickFilter(prev => prev === f.id ? null : f.id)}
                  className={`inline-flex items-center gap-1.5 text-[11px] font-medium px-3 py-1.5 rounded-full border whitespace-nowrap shrink-0 transition-colors ${quickFilter === f.id
                      ? `${f.activeColor} text-white`
                      : `bg-background text-muted-foreground border-border ${f.hoverColor}`
                    }`}
                >
                  {f.icon}
                  {f.label}
                  {f.count != null && f.count > 0 && (
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${quickFilter === f.id ? f.activeCountBg : f.countBg}`}>
                      {f.count}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Arama + Seçici Filtreler */}
            <div className="flex flex-col gap-2">
              <Input
                placeholder="Ürün adı veya satıcı ile ara..."
                value={searchText}
                onChange={e => setSearchText(e.target.value)}
                className="w-full h-9 text-sm"
              />
              <div className="flex gap-2">
                <Select value={selectedProduct || "all"} onValueChange={val => setSelectedProduct(val === "all" ? "" : val)}>
                  <SelectTrigger className="flex-1 h-9 text-xs sm:text-sm min-w-0">
                    <SelectValue placeholder="Tüm Ürünler" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tüm Ürünler</SelectItem>
                    {productNames.map(name => <SelectItem key={name} value={name}>{name}</SelectItem>)}
                  </SelectContent>
                </Select>
                <Select value={selectedSeller || "all"} onValueChange={val => setSelectedSeller(val === "all" ? "" : val)}>
                  <SelectTrigger className="flex-1 h-9 text-xs sm:text-sm min-w-0">
                    <SelectValue placeholder="Tüm Satıcılar" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tüm Satıcılar</SelectItem>
                    {sellers.map(seller => <SelectItem key={seller} value={seller}>{seller}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Aktif filtre pill'leri */}
            {(searchText || selectedProduct || selectedSeller) && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[11px] text-muted-foreground">Filtre:</span>
                {searchText && (
                  <button onClick={() => setSearchText("")} className="inline-flex items-center gap-1 bg-blue-50 text-blue-700 border border-blue-200 text-[11px] font-medium px-2 py-0.5 rounded-full hover:bg-blue-100">
                    "{searchText.length > 15 ? searchText.slice(0, 15) + "…" : searchText}"
                    <X className="h-2.5 w-2.5" />
                  </button>
                )}
                {selectedProduct && (
                  <button onClick={() => setSelectedProduct("")} className="inline-flex items-center gap-1 bg-emerald-50 text-emerald-700 border border-emerald-200 text-[11px] font-medium px-2 py-0.5 rounded-full hover:bg-emerald-100">
                    {selectedProduct.length > 18 ? selectedProduct.slice(0, 18) + "…" : selectedProduct}
                    <X className="h-2.5 w-2.5" />
                  </button>
                )}
                {selectedSeller && (
                  <button onClick={() => setSelectedSeller("")} className="inline-flex items-center gap-1 bg-amber-50 text-amber-700 border border-amber-200 text-[11px] font-medium px-2 py-0.5 rounded-full hover:bg-amber-100">
                    {selectedSeller}
                    <X className="h-2.5 w-2.5" />
                  </button>
                )}
                {[searchText, selectedProduct, selectedSeller].filter(Boolean).length >= 2 && (
                  <button onClick={() => { setSearchText(""); setSelectedProduct(""); setSelectedSeller(""); }}
                    className="text-[11px] text-muted-foreground hover:text-foreground underline underline-offset-2">
                    Temizle
                  </button>
                )}
              </div>
            )}

            {/* Seçim aksiyon barı */}
            {selectedRows.size > 0 && (
              <div className="flex items-center justify-between bg-emerald-50 border border-emerald-200 rounded-lg px-3 py-2">
                <span className="text-xs sm:text-sm font-medium text-emerald-700">{selectedRows.size} seçildi</span>
                <div className="flex items-center gap-2">
                  <button onClick={() => setSelectedRows(new Set())} className="text-xs text-emerald-600 hover:text-emerald-800">Temizle</button>
                  <button onClick={downloadSelected} className="inline-flex items-center gap-1.5 bg-emerald-600 text-white text-xs font-medium px-2.5 py-1.5 rounded-md hover:bg-emerald-700">
                    <Download className="h-3 w-3" /> İndir
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* ══ İÇERİK ═══════════════════════════════════════════════════════ */}
          {loading ? (
            <div className="flex justify-center items-center py-16">
              <RefreshCw className="h-7 w-7 animate-spin text-muted-foreground" />
              <span className="ml-2 text-sm text-muted-foreground">Yükleniyor...</span>
            </div>
          ) : filteredProducts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
              <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-muted-foreground">
                  <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-medium mb-1">{searchText ? `"${searchText}" bulunamadı` : "Ürün bulunamadı"}</p>
                <p className="text-xs text-muted-foreground">Filtreyi değiştirmeyi deneyin</p>
              </div>
              <button onClick={() => { setSearchText(""); setSelectedProduct(""); setSelectedSeller(""); setQuickFilter(null); }}
                className="text-sm text-muted-foreground border border-border rounded-lg px-4 py-2 hover:bg-muted">
                Tüm filtreleri temizle
              </button>
            </div>
          ) : (
            <>
              {/* ── DESKTOP TABLO (md ve üzeri) ── */}
              <div className="hidden md:block border rounded-lg overflow-hidden overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-10 px-3">
                        <input type="checkbox" className="rounded border-border cursor-pointer"
                          checked={selectedRows.size === paginatedProducts.length && paginatedProducts.length > 0}
                          onChange={toggleSelectAll} />
                      </TableHead>
                      <TableHead className="w-10 px-2"></TableHead>
                      <TableHead className="text-left px-4">Ürün Adı</TableHead>
                      <TableHead className="text-right px-4 cursor-pointer select-none hover:text-foreground" onClick={() => toggleSort("buyBoxPrice")}>
                        <div className="flex items-center justify-end gap-1">Buy Box Fiyat <SortIcon field="buyBoxPrice" /></div>
                      </TableHead>
                      <TableHead className="text-left px-4 w-[140px]">Buy Box Satıcı</TableHead>
                      <TableHead className="text-center px-4 cursor-pointer select-none hover:text-foreground" onClick={() => toggleSort("rating")}>
                        <div className="flex items-center justify-center gap-1">Rating <SortIcon field="rating" /></div>
                      </TableHead>
                      <TableHead className="text-center px-4 cursor-pointer select-none hover:text-foreground" onClick={() => toggleSort("sellerCount")}>
                        <div className="flex items-center justify-center gap-1">Satıcı <SortIcon field="sellerCount" /></div>
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paginatedProducts.map((product) => {
                      const isExpanded = expandedRow === product.productName;
                      const hasMultipleSellers = product.allSellers.length > 1;
                      const iAmBuyBox = product.buyBoxSeller.trim().toLowerCase() === myName;
                      const iAmSeller = product.allSellers.some(s => s.sellerName.trim().toLowerCase() === myName);
                      return (
                        <Fragment key={product.productName}>
                          <TableRow
                            onClick={() => { if (hasMultipleSellers) toggleRow(product.productName); }}
                            className={`transition-all duration-200 ${hasMultipleSellers ? "cursor-pointer" : ""} ${isExpanded ? "bg-muted/60 border-l-2 border-l-emerald-500"
                                : expandedRow !== null ? "opacity-35 pointer-events-none"
                                  : hasMultipleSellers ? "hover:bg-muted/30" : ""
                              }`}
                          >
                            <TableCell className="w-10 px-3" onClick={e => e.stopPropagation()}>
                              <input type="checkbox" className="rounded border-border cursor-pointer"
                                checked={selectedRows.has(product.productName)}
                                onChange={() => toggleRowSelect(product.productName)} />
                            </TableCell>
                            <TableCell className="w-10 px-2">
                              {hasMultipleSellers
                                ? isExpanded ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                : <div className="w-4" />}
                            </TableCell>
                            <TableCell className="min-w-0 max-w-0 px-4">
                              <div className="flex items-center gap-2 min-w-0">
                                <TooltipProvider delayDuration={300}>
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <span className="truncate max-w-[340px] block font-medium">{product.productName}</span>
                                    </TooltipTrigger>
                                    <TooltipContent side="top" className="max-w-[420px] text-xs">{product.productName}</TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                                {iAmSeller && !iAmBuyBox && (
                                  <span className="text-[10px] bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full shrink-0">Kaybettim</span>
                                )}
                                {product.productLink && (
                                  <a href={product.productLink} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()} className="text-blue-600 hover:text-blue-800 shrink-0">
                                    <ExternalLink className="h-4 w-4" />
                                  </a>
                                )}
                              </div>
                            </TableCell>
                            <TableCell className="text-right px-4 font-semibold text-green-600">
                              ₺{product.buyBoxPrice.toFixed(2)}
                            </TableCell>
                            <TableCell className="px-4">
                              <TooltipProvider delayDuration={300}>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Badge className={`max-w-[120px] truncate block text-center text-xs ${iAmBuyBox ? "bg-emerald-600 text-white" : "bg-red-500 text-white"}`}>
                                      {product.buyBoxSeller}
                                    </Badge>
                                  </TooltipTrigger>
                                  <TooltipContent side="top" className="text-xs">{product.buyBoxSeller}</TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            </TableCell>
                            <TableCell className="text-center px-4">
                              <div className="flex items-center justify-center gap-1">
                                <Star className="h-3.5 w-3.5 fill-yellow-400 text-yellow-400" />
                                <span className="text-sm">{product.buyBoxRating}</span>
                              </div>
                            </TableCell>
                            <TableCell className="text-center px-4">
                              <div className="inline-flex items-center justify-center gap-1">
                                <span className="font-medium tabular-nums text-sm">{product.allSellers.length}</span>
                                {product.allSellers.length > 1 && (
                                  <ChevronDown className={`h-3 w-3 text-muted-foreground transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`} />
                                )}
                              </div>
                            </TableCell>
                          </TableRow>

                          {isExpanded && (
                            <TableRow className="border-l-2 border-l-emerald-500">
                              <TableCell colSpan={7} className="p-0 bg-muted/20 animate-in fade-in-0 slide-in-from-top-1 duration-200">
                                <div className="p-4 flex flex-col gap-2">
                                  {product.allSellers.map((seller, idx) => {
                                    const discount = Math.round((1 - seller.finalPrice / seller.originalPrice) * 100);
                                    const isMe = seller.sellerName.trim().toLowerCase() === myName;
                                    const priceDiff = seller.finalPrice - product.allSellers[0].finalPrice;
                                    return (
                                      <div key={idx} className={`bg-white border rounded-xl p-4 grid grid-cols-4 gap-4 items-center transition-all ${seller.isBuyBox ? 'border-emerald-300 bg-emerald-50/50'
                                          : isMe ? 'border-red-200 bg-red-50/30'
                                            : 'hover:border-border'
                                        }`}>
                                        <div className="flex items-center gap-3 min-w-0">
                                          <div className={`w-9 h-9 rounded-full flex items-center justify-center text-[11px] font-semibold shrink-0 ${seller.isBuyBox ? 'bg-emerald-500 text-white' : isMe ? 'bg-red-400 text-white' : 'bg-muted text-muted-foreground'}`}>
                                            {getInitials(seller.sellerName)}
                                          </div>
                                          <div className="flex flex-col min-w-0">
                                            <span className="font-medium text-sm truncate max-w-[130px]">{seller.sellerName}</span>
                                            {seller.isBuyBox && <span className="bg-emerald-500 text-white text-[10px] rounded-full px-2 py-0.5 w-fit mt-0.5">Buy Box</span>}
                                            {isMe && !seller.isBuyBox && <span className="bg-red-400 text-white text-[10px] rounded-full px-2 py-0.5 w-fit mt-0.5">Ben (+₺{priceDiff.toFixed(0)})</span>}
                                          </div>
                                        </div>
                                        <div className="flex items-center gap-2 flex-wrap">
                                          <span className="line-through text-muted-foreground text-sm">₺{seller.originalPrice.toFixed(2)}</span>
                                          <span className="text-muted-foreground text-sm">→</span>
                                          <span className="font-semibold">₺{seller.finalPrice.toFixed(2)}</span>
                                          {discount > 0 && seller.originalPrice !== seller.finalPrice && (
                                            <span className="bg-emerald-50 text-emerald-700 text-[11px] rounded-full px-2 py-0.5">%{discount}</span>
                                          )}
                                        </div>
                                        <div className="flex gap-1.5 flex-wrap">
                                          {seller.coupon !== "-" && <div className="border rounded-md px-2 py-0.5 text-[11px] text-muted-foreground flex items-center gap-1"><TagIcon className="h-3 w-3" />{seller.coupon}</div>}
                                          {seller.cartDiscount !== "-" && <div className="border rounded-md px-2 py-0.5 text-[11px] text-muted-foreground flex items-center gap-1"><ShoppingCart className="h-3 w-3" />{seller.cartDiscount}</div>}
                                        </div>
                                        <div className="text-right flex items-center justify-end gap-1">
                                          <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                                          <span className="text-sm">{seller.rating}</span>
                                        </div>
                                      </div>
                                    );
                                  })}
                                </div>
                              </TableCell>
                            </TableRow>
                          )}
                        </Fragment>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>

              {/* ── MOBİL KART LİSTESİ (md altı) ── */}
              <div className="md:hidden flex flex-col gap-2">
                {paginatedProducts.map((product) => {
                  const isExpanded = expandedRow === product.productName;
                  const iAmBuyBox = product.buyBoxSeller.trim().toLowerCase() === myName;
                  const iAmSeller = product.allSellers.some(s => s.sellerName.trim().toLowerCase() === myName);
                  return (
                    <div key={product.productName} className={`border rounded-xl overflow-hidden ${isExpanded ? "border-emerald-400" : ""}`}>
                      {/* Kart başlığı */}
                      <div
                        className="flex items-start gap-2.5 p-3 active:bg-muted/20"
                        onClick={() => product.allSellers.length > 1 && toggleRow(product.productName)}
                      >
                        <input
                          type="checkbox"
                          className="rounded border-border cursor-pointer mt-1 shrink-0"
                          checked={selectedRows.has(product.productName)}
                          onChange={() => toggleRowSelect(product.productName)}
                          onClick={e => e.stopPropagation()}
                        />
                        <div className="flex-1 min-w-0">
                          {/* Ürün adı */}
                          <div className="flex items-start gap-1.5 mb-1.5">
                            <span className="font-medium text-sm leading-snug line-clamp-2 flex-1">{product.productName}</span>
                            {product.productLink && (
                              <a href={product.productLink} target="_blank" rel="noopener noreferrer"
                                onClick={e => e.stopPropagation()} className="text-blue-500 shrink-0 mt-0.5">
                                <ExternalLink className="h-3.5 w-3.5" />
                              </a>
                            )}
                          </div>
                          {/* Alt satır: fiyat + satıcı + meta */}
                          <div className="flex items-center justify-between gap-2 flex-wrap">
                            <div className="flex items-center gap-2">
                              <span className="text-base font-bold text-green-600">₺{product.buyBoxPrice.toFixed(2)}</span>
                              <Badge className={`text-[10px] px-1.5 py-0 h-4 leading-none ${iAmBuyBox ? "bg-emerald-600 text-white" : "bg-red-500 text-white"}`}>
                                {product.buyBoxSeller.length > 10 ? product.buyBoxSeller.slice(0, 10) + "…" : product.buyBoxSeller}
                              </Badge>
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                              {iAmSeller && !iAmBuyBox && (
                                <span className="text-[10px] bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full">Kaybettim</span>
                              )}
                              <div className="flex items-center gap-0.5 text-xs text-muted-foreground">
                                <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                                <span>{product.buyBoxRating}</span>
                              </div>
                              <span className="text-xs text-muted-foreground">{product.allSellers.length}s</span>
                              {product.allSellers.length > 1 && (
                                <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`} />
                              )}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Genişletilmiş satıcı listesi (mobil) */}
                      {isExpanded && (
                        <div className="border-t bg-muted/10 p-2.5 flex flex-col gap-2 animate-in fade-in-0 duration-200">
                          {product.allSellers.map((seller, idx) => {
                            const isMe = seller.sellerName.trim().toLowerCase() === myName;
                            const priceDiff = seller.finalPrice - product.allSellers[0].finalPrice;
                            const discount = Math.round((1 - seller.finalPrice / seller.originalPrice) * 100);
                            return (
                              <div key={idx} className={`bg-white border rounded-lg p-3 ${seller.isBuyBox ? 'border-emerald-300 bg-emerald-50/40'
                                  : isMe ? 'border-red-200 bg-red-50/30'
                                    : 'border-border'
                                }`}>
                                {/* Satıcı başlığı */}
                                <div className="flex items-center justify-between mb-2">
                                  <div className="flex items-center gap-2 min-w-0">
                                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 ${seller.isBuyBox ? 'bg-emerald-500 text-white' : isMe ? 'bg-red-400 text-white' : 'bg-muted text-muted-foreground'}`}>
                                      {getInitials(seller.sellerName)}
                                    </div>
                                    <span className="font-medium text-xs truncate max-w-[130px]">{seller.sellerName}</span>
                                  </div>
                                  <div className="flex items-center gap-1.5 shrink-0">
                                    {seller.isBuyBox && <span className="bg-emerald-500 text-white text-[9px] rounded-full px-1.5 py-0.5">Buy Box</span>}
                                    {isMe && !seller.isBuyBox && <span className="bg-red-400 text-white text-[9px] rounded-full px-1.5 py-0.5">+₺{priceDiff.toFixed(0)}</span>}
                                    <div className="flex items-center gap-0.5">
                                      <Star className="h-3 w-3 fill-amber-400 text-amber-400" />
                                      <span className="text-xs">{seller.rating}</span>
                                    </div>
                                  </div>
                                </div>
                                {/* Fiyat + etiketler */}
                                <div className="flex items-center gap-1.5 flex-wrap">
                                  <span className="line-through text-muted-foreground text-xs">₺{seller.originalPrice.toFixed(2)}</span>
                                  <span className="text-muted-foreground text-xs">→</span>
                                  <span className="font-semibold text-sm">₺{seller.finalPrice.toFixed(2)}</span>
                                  {discount > 0 && seller.originalPrice !== seller.finalPrice && (
                                    <span className="bg-emerald-50 text-emerald-700 text-[10px] rounded-full px-1.5 py-0.5">%{discount}</span>
                                  )}
                                  {seller.coupon !== "-" && (
                                    <span className="border rounded px-1.5 py-0.5 text-[10px] text-muted-foreground flex items-center gap-0.5">
                                      <TagIcon className="h-2.5 w-2.5" />{seller.coupon}
                                    </span>
                                  )}
                                  {seller.cartDiscount !== "-" && (
                                    <span className="border rounded px-1.5 py-0.5 text-[10px] text-muted-foreground flex items-center gap-0.5">
                                      <ShoppingCart className="h-2.5 w-2.5" />{seller.cartDiscount}
                                    </span>
                                  )}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* ── Pagination ── */}
              <div className="flex items-center justify-between pt-2 border-t gap-2 flex-wrap">
                <span className="text-xs text-muted-foreground">
                  <span className="hidden sm:inline">{filteredProducts.length} üründen </span>
                  {(currentPage - 1) * pageSize + 1}–{Math.min(currentPage * pageSize, filteredProducts.length)}
                </span>
                <div className="flex items-center gap-1">
                  <Button variant="outline" size="sm" className="h-7 px-2.5 text-xs" disabled={currentPage === 1} onClick={() => setCurrentPage(p => p - 1)}>←</Button>
                  {/* Mobil: X/Y göster */}
                  <span className="text-xs text-muted-foreground px-2 md:hidden">{currentPage}/{totalPages}</span>
                  {/* Desktop: sayfa butonları */}
                  <div className="hidden md:flex items-center gap-1">
                    {Array.from({ length: totalPages }, (_, i) => i + 1)
                      .filter(p => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 1)
                      .reduce((acc, p, i, arr) => {
                        if (i > 0 && p - arr[i - 1] > 1) acc.push(<span key={'e' + p} className="px-1 text-muted-foreground text-xs">…</span>);
                        acc.push(
                          <Button key={p} variant={p === currentPage ? "default" : "outline"} size="sm" className="h-7 w-7 p-0 text-xs" onClick={() => setCurrentPage(p)}>{p}</Button>
                        );
                        return acc;
                      }, [] as React.ReactNode[])}
                  </div>
                  <Button variant="outline" size="sm" className="h-7 px-2.5 text-xs" disabled={currentPage === totalPages} onClick={() => setCurrentPage(p => p + 1)}>→</Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
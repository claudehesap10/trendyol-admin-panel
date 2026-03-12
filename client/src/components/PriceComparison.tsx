import { useMemo } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingDown, TrendingUp, Star } from "lucide-react";

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

interface PriceComparisonProps {
  sellers: SellerInfo[];
}

export function PriceComparison({ sellers }: PriceComparisonProps) {
  const sortedSellers = useMemo(() => {
    return [...sellers].sort((a, b) => a.finalPrice - b.finalPrice);
  }, [sellers]);

  const minPrice = Math.min(...sellers.map(s => s.finalPrice));
  const maxPrice = Math.max(...sellers.map(s => s.finalPrice));
  const priceDiff = maxPrice - minPrice;
  const priceDiffPercent = minPrice > 0 ? Math.round((priceDiff / minPrice) * 100) : 0;

  // 2 veya daha az satıcı: Kart görünümü
  if (sellers.length <= 2) {
    return (
      <div className="space-y-4 mb-6">
        <h4 className="font-semibold text-sm text-slate-700">Fiyat Karşılaştırması</h4>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sortedSellers.map((seller, idx) => {
            const isLowest = seller.finalPrice === minPrice;
            const discountPercent = seller.originalPrice > 0 
              ? Math.round((1 - seller.finalPrice / seller.originalPrice) * 100) 
              : 0;

            return (
              <Card 
                key={idx} 
                className={`relative overflow-hidden ${isLowest ? 'border-2 border-green-500 shadow-lg' : 'border-slate-200'}`}
              >
                {isLowest && (
                  <div className="absolute top-3 left-3">
                    <Badge className="bg-green-500">En Uygun</Badge>
                  </div>
                )}
                <CardContent className="pt-6">
                  <div className="space-y-3">
                    {/* Satıcı Adı */}
                    <div className="flex items-start justify-between gap-2">
                      <h5 className="font-semibold text-slate-900 flex-1 mt-6">{seller.sellerName}</h5>
                      {seller.isBuyBox && (
                        <Badge variant="default" className="text-xs">Buy Box</Badge>
                      )}
                    </div>

                    {/* Orijinal Fiyat */}
                    {seller.originalPrice !== seller.finalPrice && (
                      <div className="text-sm text-muted-foreground line-through">
                        {seller.originalPrice.toLocaleString('tr-TR')} ₺
                      </div>
                    )}

                    {/* Son Fiyat */}
                    <div className={`text-3xl font-bold ${isLowest ? 'text-green-600' : 'text-slate-900'}`}>
                      {seller.finalPrice.toLocaleString('tr-TR')} ₺
                    </div>

                    {/* İndirim Badge */}
                    {discountPercent > 0 && (
                      <Badge variant="secondary" className="text-xs">
                        <TrendingDown className="h-3 w-3 mr-1" />
                        %{discountPercent} indirim
                      </Badge>
                    )}

                    {/* Rating */}
                    <div className="flex items-center gap-1 text-sm">
                      <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                      <span className="font-medium">{seller.rating}</span>
                      <span className="text-muted-foreground">/ 5.0</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Fiyat Farkı Bar */}
        {sellers.length === 2 && priceDiff > 0 && (
          <Card className="bg-slate-50">
            <CardContent className="pt-4 pb-4">
              <div className="flex items-center justify-between text-sm mb-2">
                <span className="text-muted-foreground">Fiyat Farkı</span>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-xs">
                    {priceDiff.toLocaleString('tr-TR')} ₺
                  </Badge>
                  <Badge variant="outline" className="text-xs">
                    %{priceDiffPercent}
                  </Badge>
                </div>
              </div>
              <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-green-500 to-red-500"
                  style={{ width: '100%' }}
                />
              </div>
              <div className="flex items-center justify-between text-xs text-muted-foreground mt-1">
                <span>En ucuz</span>
                <span>En pahalı</span>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    );
  }

  // 3 veya daha fazla satıcı: Bar chart görünümü
  const chartData = sortedSellers.map(seller => ({
    name: seller.sellerName.length > 25 ? seller.sellerName.substring(0, 22) + '...' : seller.sellerName,
    fullName: seller.sellerName,
    price: seller.finalPrice,
    isBuyBox: seller.isBuyBox,
  }));

  const domain = [
    Math.floor(minPrice * 0.97),
    Math.ceil(maxPrice * 1.01)
  ];

  return (
    <div className="space-y-4 mb-6">
      <h4 className="font-semibold text-sm text-slate-700">Fiyat Karşılaştırması ({sellers.length} Satıcı)</h4>
      
      {/* Metrics Cards */}
      <div className="grid grid-cols-3 gap-3">
        <Card className="border-green-200 bg-green-50">
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-green-700 font-medium mb-1">En Ucuz</div>
            <div className="text-xl font-bold text-green-600">
              {minPrice.toLocaleString('tr-TR')} ₺
            </div>
          </CardContent>
        </Card>

        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-red-700 font-medium mb-1">En Pahalı</div>
            <div className="text-xl font-bold text-red-600">
              {maxPrice.toLocaleString('tr-TR')} ₺
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-slate-50">
          <CardContent className="pt-4 pb-4">
            <div className="text-xs text-slate-700 font-medium mb-1">Fark</div>
            <div className="text-lg font-bold text-slate-900">
              {priceDiff.toLocaleString('tr-TR')} ₺
            </div>
            <div className="text-xs text-muted-foreground">%{priceDiffPercent}</div>
          </CardContent>
        </Card>
      </div>

      {/* Bar Chart */}
      <Card>
        <CardContent className="pt-6">
          <ResponsiveContainer width="100%" height={Math.max(300, sellers.length * 50)}>
            <BarChart 
              data={chartData} 
              layout="vertical"
              margin={{ top: 5, right: 80, left: 5, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} />
              <XAxis 
                type="number" 
                domain={domain}
                tickFormatter={(value) => `${value.toLocaleString('tr-TR')}₺`}
              />
              <YAxis 
                type="category" 
                dataKey="name" 
                width={150}
                tick={{ fontSize: 12 }}
              />
              <Tooltip 
                formatter={(value: number, name: string, props: any) => [
                  `${value.toLocaleString('tr-TR')} ₺${props.payload.isBuyBox ? ' ⭐' : ''}`,
                  props.payload.fullName
                ]}
                contentStyle={{ 
                  backgroundColor: 'rgba(0, 0, 0, 0.8)', 
                  border: 'none', 
                  borderRadius: '8px',
                  color: 'white'
                }}
              />
              <Bar dataKey="price" radius={[0, 8, 8, 0]}>
                {chartData.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={entry.isBuyBox ? '#16a34a' : '#3b82f6'} 
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}

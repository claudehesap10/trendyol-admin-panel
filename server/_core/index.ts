import "dotenv/config";
import express from "express";
import { createServer } from "http";
import net from "net";
import { createExpressMiddleware } from "@trpc/server/adapters/express";
import { registerOAuthRoutes } from "./oauth";
import { appRouter } from "../routers";
import { createContext } from "./context";
import { serveStatic, setupVite } from "./vite";

function isPortAvailable(port: number): Promise<boolean> {
  return new Promise(resolve => {
    const server = net.createServer();
    server.listen(port, () => {
      server.close(() => resolve(true));
    });
    server.on("error", () => resolve(false));
  });
}

async function findAvailablePort(startPort: number = 3000): Promise<number> {
  for (let port = startPort; port < startPort + 20; port++) {
    if (await isPortAvailable(port)) {
      return port;
    }
  }
  throw new Error(`No available port found starting from ${startPort}`);
}

async function startServer() {
  const app = express();
  const server = createServer(app);
  // Configure body parser with larger size limit for file uploads
  app.use(express.json({ limit: "50mb" }));
  app.use(express.urlencoded({ limit: "50mb", extended: true }));
  // OAuth callback under /api/oauth/callback
  registerOAuthRoutes(app);
  
  // Helper function: GitHub'dan Excel indirip parse eder
  async function fetchAndParseExcel(release: any) {
    const excelFile = release.assets?.find((asset: any) => asset.name.endsWith(".xlsx"));
    if (!excelFile) return null;

    // Private repo desteği için asset API URL'ini kullanıyoruz
    const assetUrl = excelFile.url;
    const fileResponse = await fetch(assetUrl, {
      headers: {
        Accept: "application/octet-stream",
        Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
      },
    });

    if (!fileResponse.ok) throw new Error(`Failed to download Excel for ${release.tag_name}`);

    const buffer = await fileResponse.arrayBuffer();
    const XLSX = await import("xlsx");
    const workbook = XLSX.read(new Uint8Array(buffer), { type: "array" });
    const sheetName = "Tarama Raporu";
    const worksheet = workbook.Sheets[sheetName] || workbook.Sheets[workbook.SheetNames[0]];
    
    const range = XLSX.utils.decode_range(worksheet["!ref"] || "A1");
    const headers: string[] = [];
    for (let col = range.s.c; col <= range.e.c; col++) {
      const cellAddress = XLSX.utils.encode_col(col) + "4";
      const cell = worksheet[cellAddress];
      headers.push(cell?.v?.toString() || "");
    }
    
    const data: any[] = [];
    for (let row = 5; row <= range.e.r; row++) {
      const rowData: any = {};
      for (let col = range.s.c; col <= range.e.c; col++) {
        const cellAddress = XLSX.utils.encode_col(col) + row;
        const cell = worksheet[cellAddress];
        const header = headers[col - range.s.c];
        if (header) {
          rowData[header] = cell?.v ?? "";
        }
      }
      if (Object.values(rowData).some((v) => v !== "")) {
        data.push(rowData);
      }
    }
    return data;
  }

  // Reports API endpoint
  app.get("/api/reports/latest", async (req, res) => {
    try {
      const response = await fetch(
        "https://api.github.com/repos/claudehesap10/trendyol-admin-panel/releases",
        {
          headers: {
            Accept: "application/vnd.github.v3+json",
            Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
          },
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Failed to fetch releases: ${response.status} - ${errorText}`);
      }

      const releases = await response.json();
      if (releases.length === 0) return res.json({ data: [], releases: [] });

      const data = await fetchAndParseExcel(releases[0]);
      res.json({ data: data || [], releases });
    } catch (error) {
      console.error("Error fetching reports:", error);
      res.status(500).json({ error: "Failed to fetch reports" });
    }
  });

  // Comparison API - Artık Node.js üzerinden çalışıyor (Python servisine ihtiyaç duymaz)
  app.get("/api/reports/compare", async (req, res) => {
    try {
      const showAll = req.query.show_all === "true";
      
      const response = await fetch(
        "https://api.github.com/repos/claudehesap10/trendyol-admin-panel/releases",
        {
          headers: {
            Accept: "application/vnd.github.v3+json",
            Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
          },
        }
      );

      if (!response.ok) throw new Error("GitHub releases could not be fetched");
      const releases = await response.json();

      if (releases.length < 2) {
        return res.json({ 
          success: false, 
          message: "Karşılaştırma için en az iki rapor (release) gerekiyor." 
        });
      }

      const [newRelease, oldRelease] = releases;
      const [newData, oldData] = await Promise.all([
        fetchAndParseExcel(newRelease),
        fetchAndParseExcel(oldRelease)
      ]);

      if (!newData || !oldData) {
        throw new Error("Excel files could not be parsed");
      }

      // Karşılaştırma Mantığı
      const oldMap = new Map();
      oldData.forEach((item: any) => {
        const key = `${item["Ürün Adı"]}_${item["Satıcı"]}`;
        oldMap.set(key, item);
      });

      const changes: any[] = [];
      const stats = { "İndirim": 0, "Zam": 0, "Sabit": 0, "Yeni Satıcı": 0, "Total": newData.length };

      newData.forEach((row: any) => {
        const key = `${row["Ürün Adı"]}_${row["Satıcı"]}`;
        const oldRow = oldMap.get(key);

        const newPrice = parseFloat(row["Son Fiyat (TL)"]) || 0;
        const oldPrice = oldRow ? parseFloat(oldRow["Son Fiyat (TL)"]) : null;

        let status: "İndirim" | "Zam" | "Sabit" | "Yeni Satıcı" = "Sabit";
        let diff = 0;
        let percent = 0;

        if (oldPrice === null) {
          status = "Yeni Satıcı";
        } else {
          diff = newPrice - oldPrice;
          if (Math.abs(diff) > 0.05) {
            percent = (diff / oldPrice) * 100;
            status = diff > 0 ? "Zam" : "İndirim";
          } else {
            status = "Sabit";
            diff = 0;
            percent = 0;
          }
        }

        stats[status]++;

        if (showAll || status !== "Sabit") {
          changes.push({
            product: row["Ürün Adı"],
            barcode: row["Barkod"] || (oldRow ? oldRow["Barkod"] : ""),
            url: row["Ürün Linki"],
            seller: row["Satıcı"],
            new_price: newPrice,
            old_price: oldPrice,
            diff: Number(diff.toFixed(2)),
            percent: Number(percent.toFixed(2)),
            status: status
          });
        }
      });

      res.json({
        success: true,
        data: {
          summary: {
            new_report: { tag: newRelease.tag_name, date: newRelease.published_at },
            old_report: { tag: oldRelease.tag_name, date: oldRelease.published_at },
            stats
          },
          changes
        }
      });

    } catch (error: any) {
      console.error("Comparison error:", error);
      res.status(500).json({ success: false, message: error.message });
    }
  });
  
  // tRPC API
  app.use(
    "/api/trpc",
    createExpressMiddleware({
      router: appRouter,
      createContext,
    })
  );
  // development mode uses Vite, production mode uses static files
  if (process.env.NODE_ENV === "development") {
    await setupVite(app, server);
  } else {
    serveStatic(app);
  }

  const preferredPort = parseInt(process.env.PORT || "3000");
  const port = await findAvailablePort(preferredPort);

  if (port !== preferredPort) {
    console.log(`Port ${preferredPort} is busy, using port ${port} instead`);
  }

  server.listen(port, "0.0.0.0", () => {
    console.log(`Server running on http://localhost:${port}/`);
  });
}

startServer().catch(console.error);

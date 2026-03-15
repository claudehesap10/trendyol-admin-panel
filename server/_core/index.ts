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

      if (releases.length === 0) {
        return res.json({ data: [], releases: [] });
      }

      const latestRelease = releases[0];
      const excelFile = latestRelease.assets?.find((asset: any) =>
        asset.name.endsWith(".xlsx")
      );

      if (!excelFile) {
        return res.json({ data: [], releases });
      }

      const downloadUrl = `https://github.com/claudehesap10/trendyol-admin-panel/releases/download/${latestRelease.tag_name}/${excelFile.name}`;
      const fileResponse = await fetch(downloadUrl);

      if (!fileResponse.ok) throw new Error("Failed to download Excel");

      const buffer = await fileResponse.arrayBuffer();

      // Import XLSX dynamically
      const XLSX = await import("xlsx");
      const workbook = XLSX.read(new Uint8Array(buffer), { type: "array" });
      const sheetName = "Tarama Raporu";
      const worksheet = workbook.Sheets[sheetName] || workbook.Sheets[workbook.SheetNames[0]];
      
      // 4. satırdan başlıkları oku
      const range = XLSX.utils.decode_range(worksheet["!ref"] || "A1");
      const headers: string[] = [];
      for (let col = range.s.c; col <= range.e.c; col++) {
        const cellAddress = XLSX.utils.encode_col(col) + "4";
        const cell = worksheet[cellAddress];
        headers.push(cell?.v?.toString() || "");
      }
      
      // 5. satırdan veriyi oku
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

      res.json({ data, releases });
    } catch (error) {
      console.error("Error fetching reports:", error);
      res.status(500).json({ error: "Failed to fetch reports" });
    }
  });

  // Comparison API Proxy (Python'a yönlendirme)
  app.get("/api/reports/compare", async (req, res) => {
    try {
      const showAll = req.query.show_all === "true";
      const pythonResponse = await fetch(
        `http://localhost:8000/api/reports/compare?show_all=${showAll}`
      );
      
      if (!pythonResponse.ok) {
        const errorText = await pythonResponse.text();
        throw new Error(`Python service error: ${pythonResponse.status} - ${errorText}`);
      }

      const result = await pythonResponse.json();
      res.json(result);
    } catch (error) {
      console.error("Comparison proxy error:", error);
      res.status(500).json({ 
        success: false, 
        message: "Karşılaştırma servisine ulaşılamıyor. Python API'nin ayakta olduğundan emin olun." 
      });
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

  server.listen(port, () => {
    console.log(`Server running on http://localhost:${port}/`);
  });
}

startServer().catch(console.error);

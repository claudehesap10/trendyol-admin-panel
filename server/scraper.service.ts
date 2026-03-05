import { exec } from "child_process";
import { promisify } from "util";
import path from "path";
import fs from "fs";

const execAsync = promisify(exec);

export class ScraperService {
  /**
   * Clone the scraper repo and run the main controller
   */
  static async runScraper(): Promise<{ success: boolean; message: string; reportPath?: string }> {
    let tempDir: string | null = null;
    
    try {
      // Create temp directory for scraper
      tempDir = path.join("/tmp", `scraper-${Date.now()}`);
      
      // Clone the repo
      console.log(`Cloning scraper repo to ${tempDir}...`);
      await execAsync(`git clone https://github.com/claudehesap10/trendyol-admin-panel.git ${tempDir}`);
      
      // Create logs directory
      const logsDir = path.join(tempDir, "logs");
      if (!fs.existsSync(logsDir)) {
        fs.mkdirSync(logsDir, { recursive: true });
      }
      
      // Install requirements
      console.log("Installing Python dependencies...");
      await execAsync(
        `cd ${tempDir} && /usr/bin/python3.11 -m pip install --break-system-packages -q -r requirements.txt 2>/dev/null || true`,
        { maxBuffer: 10 * 1024 * 1024 }
      );
      
      // Run the main controller
      console.log("Running scraper...");
      const { stdout, stderr } = await execAsync(
        `cd ${tempDir} && /usr/bin/python3.11 controller/main_controller.py`,
        { maxBuffer: 10 * 1024 * 1024, timeout: 600000, env: { ...process.env, PYTHONHOME: "", PYTHONPATH: "" } } // 10 min timeout
      );
      
      console.log("Scraper output:", stdout);
      if (stderr) console.log("Scraper stderr:", stderr);
      
      // Find the generated report
      const reportsDir = path.join(tempDir, "reports");
      let reportPath: string | undefined;
      
      if (fs.existsSync(reportsDir)) {
        const files = fs.readdirSync(reportsDir);
        const latestFile = files
          .map(f => ({
            name: f,
            time: fs.statSync(path.join(reportsDir, f)).mtime.getTime(),
          }))
          .sort((a, b) => b.time - a.time)[0];
        
        if (latestFile) {
          reportPath = path.join(reportsDir, latestFile.name);
        }
      }
      
      return {
        success: true,
        message: "Scraper completed successfully",
        reportPath,
      };
    } catch (error) {
      console.error("Scraper error:", error);
      return {
        success: false,
        message: `Scraper failed: ${error instanceof Error ? error.message : String(error)}`,
      };
    } finally {
      // Cleanup temp directory
      if (tempDir && fs.existsSync(tempDir)) {
        try {
          await execAsync(`rm -rf ${tempDir}`);
        } catch (cleanupError) {
          console.error("Cleanup error:", cleanupError);
        }
      }
    }
  }
}

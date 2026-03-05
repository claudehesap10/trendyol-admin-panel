import { z } from "zod";
import { protectedProcedure, publicProcedure, router } from "../_core/trpc";
import { getOrCreateSettings, updateSettings, getScanHistory } from "../db";
import { GitHubService } from "../github.service";
import * as XLSX from "xlsx";

export const trendyolRouter = router({
  settings: router({
    get: protectedProcedure.query(async ({ ctx }) => {
      return await getOrCreateSettings(ctx.user.id);
    }),
    update: protectedProcedure
      .input(
        z.object({
          trendyolUrl: z.string().optional(),
          telegramToken: z.string().optional(),
          telegramChatId: z.string().optional(),
          cronExpression: z.string().optional(),
          githubToken: z.string().optional(),
          githubRepo: z.string().optional(),
          githubWorkflowId: z.string().optional(),
        })
      )
      .mutation(async ({ ctx, input }) => {
        return await updateSettings(ctx.user.id, input);
      }),
  }),

  workflows: router({
    trigger: protectedProcedure
      .input(
        z.object({
          owner: z.string(),
          repo: z.string(),
          workflowId: z.string(),
        })
      )
      .mutation(async ({ ctx, input }) => {
        const settings = await getOrCreateSettings(ctx.user.id);
        if (!settings?.githubToken) throw new Error("GitHub token not configured");

        const github = new GitHubService(settings.githubToken);
        return await github.triggerWorkflow(input.owner, input.repo, input.workflowId);
      }),

    status: protectedProcedure
      .input(
        z.object({
          owner: z.string(),
          repo: z.string(),
          runId: z.number(),
        })
      )
      .query(async ({ ctx, input }) => {
        const settings = await getOrCreateSettings(ctx.user.id);
        if (!settings?.githubToken) throw new Error("GitHub token not configured");

        const github = new GitHubService(settings.githubToken);
        return await github.getWorkflowRunStatus(input.owner, input.repo, input.runId);
      }),

    list: protectedProcedure
      .input(
        z.object({
          owner: z.string(),
          repo: z.string(),
          workflowId: z.string(),
          limit: z.number().optional(),
        })
      )
      .query(async ({ ctx, input }) => {
        const settings = await getOrCreateSettings(ctx.user.id);
        if (!settings?.githubToken) throw new Error("GitHub token not configured");

        const github = new GitHubService(settings.githubToken);
        return await github.getWorkflowRuns(input.owner, input.repo, input.workflowId, input.limit);
      }),
  }),

  history: router({
    list: protectedProcedure.query(async ({ ctx }) => {
      return await getScanHistory(ctx.user.id);
    }),
  }),

  reports: router({
    getLatest: publicProcedure.query(async () => {
      try {
        // GitHub API'den releases'ı çek
        const response = await fetch(
          "https://api.github.com/repos/claudehesap10/trendyol-admin-panel/releases",
          {
            headers: {
              Accept: "application/vnd.github.v3+json",
            },
          }
        );

        if (!response.ok) throw new Error("Failed to fetch releases");

        const releases = await response.json();

        // En son release'ı bul
        if (releases.length === 0) {
          return { data: [], releases: [] };
        }

        const latestRelease = releases[0];
        const excelFile = latestRelease.assets?.find((asset: any) =>
          asset.name.endsWith(".xlsx")
        );

        if (!excelFile) {
          return { data: [], releases };
        }

        // Excel dosyasını indir
        const downloadUrl = `https://github.com/claudehesap10/trendyol-admin-panel/releases/download/${latestRelease.tag_name}/${excelFile.name}`;
        const fileResponse = await fetch(downloadUrl);

        if (!fileResponse.ok) throw new Error("Failed to download Excel");

        const buffer = await fileResponse.arrayBuffer();

        // xlsx ile parse et
        const workbook = XLSX.read(new Uint8Array(buffer), { type: "array" });
        const worksheet = workbook.Sheets[workbook.SheetNames[0]];
        const data = XLSX.utils.sheet_to_json(worksheet);

        return { data, releases };
      } catch (error) {
        console.error("Error fetching reports:", error);
        throw new Error("Failed to fetch reports");
      }
    }),
  }),
});

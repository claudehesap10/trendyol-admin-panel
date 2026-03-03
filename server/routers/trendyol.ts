import { z } from "zod";
import { protectedProcedure, router } from "../_core/trpc";
import { getOrCreateSettings, updateSettings, getScanHistory } from "../db";
import { GitHubService } from "../github.service";

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
});

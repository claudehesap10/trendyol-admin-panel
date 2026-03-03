import { describe, expect, it, vi } from "vitest";
import { trendyolRouter } from "./trendyol";
import type { TrpcContext } from "../_core/context";

type AuthenticatedUser = NonNullable<TrpcContext["user"]>;

function createAuthContext(): TrpcContext {
  const user: AuthenticatedUser = {
    id: 1,
    openId: "test-user",
    email: "test@example.com",
    name: "Test User",
    loginMethod: "manus",
    role: "user",
    createdAt: new Date(),
    updatedAt: new Date(),
    lastSignedIn: new Date(),
  };

  const ctx: TrpcContext = {
    user,
    req: {
      protocol: "https",
      headers: {},
    } as TrpcContext["req"],
    res: {} as TrpcContext["res"],
  };

  return ctx;
}

describe("trendyol router", () => {
  describe("settings", () => {
    it("should get settings for authenticated user", async () => {
      const ctx = createAuthContext();
      const caller = trendyolRouter.createCaller(ctx);

      const result = await caller.settings.get();
      expect(result).toBeDefined();
      expect(result?.userId).toBe(ctx.user.id);
    });

    it("should update settings", async () => {
      const ctx = createAuthContext();
      const caller = trendyolRouter.createCaller(ctx);

      const updateData = {
        trendyolUrl: "https://www.trendyol.com/sr?mid=123456",
        telegramToken: "test-token",
      };

      const result = await caller.settings.update(updateData);
      expect(result).toBeDefined();
    });
  });

  describe("history", () => {
    it("should list scan history for authenticated user", async () => {
      const ctx = createAuthContext();
      const caller = trendyolRouter.createCaller(ctx);

      const result = await caller.history.list();
      expect(Array.isArray(result)).toBe(true);
    });
  });
});

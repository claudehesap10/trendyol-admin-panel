import { int, mysqlEnum, mysqlTable, text, timestamp, varchar } from "drizzle-orm/mysql-core";

/**
 * Core user table backing auth flow.
 * Extend this file with additional tables as your product grows.
 * Columns use camelCase to match both database fields and generated types.
 */
export const users = mysqlTable("users", {
  /**
   * Surrogate primary key. Auto-incremented numeric value managed by the database.
   * Use this for relations between tables.
   */
  id: int("id").autoincrement().primaryKey(),
  /** Manus OAuth identifier (openId) returned from the OAuth callback. Unique per user. */
  openId: varchar("openId", { length: 64 }).notNull().unique(),
  name: text("name"),
  email: varchar("email", { length: 320 }),
  loginMethod: varchar("loginMethod", { length: 64 }),
  role: mysqlEnum("role", ["user", "admin"]).default("user").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
  lastSignedIn: timestamp("lastSignedIn").defaultNow().notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;

export const settings = mysqlTable("settings", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull().references(() => users.id),
  trendyolUrl: text("trendyolUrl").notNull(),
  telegramToken: text("telegramToken"),
  telegramChatId: varchar("telegramChatId", { length: 64 }),
  smtpServer: varchar("smtpServer", { length: 255 }).default("smtp.gmail.com"),
  smtpPort: varchar("smtpPort", { length: 10 }).default("587"),
  smtpEmail: varchar("smtpEmail", { length: 255 }),
  smtpPassword: text("smtpPassword"),
  recipientEmails: text("recipientEmails"),
  cronExpression: varchar("cronExpression", { length: 100 }).default("0 * * * *").notNull(),
  githubToken: text("githubToken"),
  githubRepo: varchar("githubRepo", { length: 255 }),
  githubWorkflowId: varchar("githubWorkflowId", { length: 255 }),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export type Settings = typeof settings.$inferSelect;
export type InsertSettings = typeof settings.$inferInsert;

export const scanHistory = mysqlTable("scanHistory", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull().references(() => users.id),
  workflowRunId: varchar("workflowRunId", { length: 64 }).notNull(),
  status: mysqlEnum("status", ["pending", "in_progress", "completed", "failed"]).default("pending").notNull(),
  productCount: int("productCount"),
  reportUrl: text("reportUrl"),
  errorMessage: text("errorMessage"),
  telegramStatus: mysqlEnum("telegramStatus", ["pending", "success", "failed"]).default("pending"),
  emailStatus: mysqlEnum("emailStatus", ["pending", "success", "failed"]).default("pending"),
  startedAt: timestamp("startedAt").defaultNow().notNull(),
  completedAt: timestamp("completedAt"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type ScanHistory = typeof scanHistory.$inferSelect;
export type InsertScanHistory = typeof scanHistory.$inferInsert;

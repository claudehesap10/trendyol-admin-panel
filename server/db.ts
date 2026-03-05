import { eq, desc } from "drizzle-orm";
import { drizzle } from "drizzle-orm/mysql2";
import { InsertUser, users, settings, scanHistory, InsertSettings, InsertScanHistory } from "../drizzle/schema";
import { ENV } from './_core/env';

let _db: ReturnType<typeof drizzle> | null = null;

// Lazily create the drizzle instance so local tooling can run without a DB.
export async function getDb() {
  if (!_db && process.env.DATABASE_URL) {
    try {
      _db = drizzle(process.env.DATABASE_URL);
    } catch (error) {
      console.warn("[Database] Failed to connect:", error);
      _db = null;
    }
  }
  return _db;
}

export async function upsertUser(user: InsertUser): Promise<void> {
  if (!user.openId) {
    throw new Error("User openId is required for upsert");
  }

  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot upsert user: database not available");
    return;
  }

  try {
    const values: InsertUser = {
      openId: user.openId,
    };
    const updateSet: Record<string, unknown> = {};

    const textFields = ["name", "email", "loginMethod"] as const;
    type TextField = (typeof textFields)[number];

    const assignNullable = (field: TextField) => {
      const value = user[field];
      if (value === undefined) return;
      const normalized = value ?? null;
      values[field] = normalized;
      updateSet[field] = normalized;
    };

    textFields.forEach(assignNullable);

    if (user.lastSignedIn !== undefined) {
      values.lastSignedIn = user.lastSignedIn;
      updateSet.lastSignedIn = user.lastSignedIn;
    }
    if (user.role !== undefined) {
      values.role = user.role;
      updateSet.role = user.role;
    } else if (user.openId === ENV.ownerOpenId) {
      values.role = 'admin';
      updateSet.role = 'admin';
    }

    if (!values.lastSignedIn) {
      values.lastSignedIn = new Date();
    }

    if (Object.keys(updateSet).length === 0) {
      updateSet.lastSignedIn = new Date();
    }

    await db.insert(users).values(values).onDuplicateKeyUpdate({
      set: updateSet,
    });
  } catch (error) {
    console.error("[Database] Failed to upsert user:", error);
    throw error;
  }
}

export async function getUserByOpenId(openId: string) {
  const db = await getDb();
  if (!db) {
    console.warn("[Database] Cannot get user: database not available");
    return undefined;
  }

  const result = await db.select().from(users).where(eq(users.openId, openId)).limit(1);

  return result.length > 0 ? result[0] : undefined;
}

export async function getOrCreateSettings(userId: number) {
  const db = await getDb();
  if (!db) return undefined;

  let setting = await db.select().from(settings).where(eq(settings.userId, userId)).limit(1);
  
  if (setting.length === 0) {
    await db.insert(settings).values({
      userId,
      trendyolUrl: "https://www.trendyol.com/sr?mid=1126746&os=1",
      cronExpression: "0 * * * *",
    });
    setting = await db.select().from(settings).where(eq(settings.userId, userId)).limit(1);
  }
  
  return setting[0];
}

export async function updateSettings(userId: number, data: Partial<InsertSettings>) {
  const db = await getDb();
  if (!db) return undefined;
  
  const result = await db.update(settings).set(data).where(eq(settings.userId, userId));
  return result;
}

export async function getScanHistory(userId: number, limit: number = 20) {
  const db = await getDb();
  if (!db) return [];
  
  return await db.select().from(scanHistory).where(eq(scanHistory.userId, userId)).orderBy(desc(scanHistory.startedAt)).limit(limit);
}

export async function createScanHistory(userId: number, workflowRunId: string) {
  const db = await getDb();
  if (!db) return undefined;
  
  const result = await db.insert(scanHistory).values({
    userId,
    workflowRunId,
    status: "pending",
  });
  return result;
}

export async function updateScanHistory(id: number, data: Partial<InsertScanHistory>) {
  const db = await getDb();
  if (!db) return undefined;
  
  return await db.update(scanHistory).set(data).where(eq(scanHistory.id, id));
}

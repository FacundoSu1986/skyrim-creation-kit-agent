import path from "node:path";
import dotenv from "dotenv";
import { drizzle } from "drizzle-orm/node-postgres";
import { migrate } from "drizzle-orm/node-postgres/migrator";
import { Pool } from "pg";

dotenv.config();

export async function runMigrations(customDatabaseUrl?: string) {
  const databaseUrl = customDatabaseUrl || process.env.DATABASE_URL;
  if (!databaseUrl) {
    console.error("ERROR: DATABASE_URL environment variable is required for migrations.");
    throw new Error("DATABASE_URL environment variable is required for migrations.");
  }

  console.log("Connecting to database for migrations...");
  const pool = new Pool({ connectionString: databaseUrl });
  const db = drizzle(pool);

  try {
    const migrationsFolder = path.resolve(process.cwd(), "drizzle");
    console.log(`Running migrations from ${migrationsFolder}...`);
    await migrate(db, { migrationsFolder });
    console.log("Migrations applied successfully.");
  } finally {
    await pool.end();
  }
}

if (
  process.argv[1] &&
  (process.argv[1].endsWith("migrate.ts") || process.argv[1].endsWith("migrate.js"))
) {
  runMigrations().catch((err) => {
    console.error("Migration failed:", err);
    process.exit(1);
  });
}

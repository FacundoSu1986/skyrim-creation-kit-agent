import dotenv from "dotenv";
import { defineConfig } from "drizzle-kit";

dotenv.config();

const databaseUrl = process.env.DATABASE_URL;

export default defineConfig({
  dialect: "postgresql",
  schema: "./src/db/schema.ts",
  out: "./drizzle",
  dbCredentials: {
    url: databaseUrl || "",
  },
});

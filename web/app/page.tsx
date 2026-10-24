import { readFile } from "node:fs/promises";
import path from "node:path";
import Dashboard from "@/components/Dashboard";
import type { Report } from "@/lib/types";

// Mode statis: report.json demo dibaca saat build dan dirender menjadi HTML.
// Bangkitkan ulang dengan: python scripts/build_dashboard_data.py
const DATA_DIR = "demo";

export default async function Page() {
  const raw = await readFile(path.join(process.cwd(), "public", DATA_DIR, "report.json"), "utf-8");
  const report = JSON.parse(raw) as Report;
  const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
  return <Dashboard report={report} dataBase={`${base}/${DATA_DIR}`} />;
}

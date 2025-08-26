import { Suspense } from "react";
import StoreClient from "./client";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function fetchInfo(name: string) {
  const res = await fetch(`${API_BASE}/stores/info/${name}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch store info");
  return res.json() as Promise<{ name: string; model: string | null; count: number }>;
}

async function fetchEntries(name: string) {
  const res = await fetch(`${API_BASE}/stores/${name}/entries`, { cache: "no-store" });
  if (!res.ok) return { entries: [] };
  return res.json() as Promise<{ entries: { id: string; text: string }[] }>;
}

export default async function StoreDetailPage({ params }: { params: { name: string } }) {
  const name = params.name;
  const [info, entries] = await Promise.all([fetchInfo(name), fetchEntries(name)]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Store: {name}</h1>

      <div className="text-sm text-muted-foreground space-y-1">
        <p><strong>Model:</strong> {info.model ?? "Not set"}</p>
        <p><strong>Records:</strong> {info.count}</p>
      </div>

      <Suspense fallback={null}>
        <StoreClient store={name} initialEntries={entries.entries} />
      </Suspense>
    </div>
  );
}

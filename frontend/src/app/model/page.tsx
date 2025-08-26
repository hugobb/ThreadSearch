import { Suspense } from "react";
import {ModelBrowserClient} from "./client";
import type { ModelInfo } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function fetchCatalog(): Promise<ModelInfo[]> {
  const res = await fetch(`${API_BASE}/models/catalog`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load catalog");
  const data = await res.json() as { models: Record<string, Omit<ModelInfo, "id">> };
  return Object.entries(data.models).map(([id, m]) => ({ id, ...m }));
}

async function fetchLocal(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/models/local`, { cache: "no-store" });
  if (!res.ok) return [];
  const data = await res.json() as { local_models: string[] };
  return data.local_models;
}

export default async function ModelPage() {
  const [catalog, localModels] = await Promise.all([fetchCatalog(), fetchLocal()]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Available Models</h1>

      {/* The inputs & actions live in a small client component */}
      <Suspense fallback={<div>Loading…</div>}>
        <ModelBrowserClient catalog={catalog} localModels={localModels} />
      </Suspense>
    </div>
  );
}

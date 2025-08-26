import Link from "next/link";
import { Suspense } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import StoresClient from "./client";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function fetchStores() {
  const res = await fetch(`${API_BASE}/stores/list`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch stores list");
  const data = (await res.json()) as { stores: string[] };

  // fetch info for each store
  const infos = await Promise.all(
    data.stores.map(async (name) => {
      try {
        const r = await fetch(`${API_BASE}/stores/info/${name}`, { cache: "no-store" });
        if (!r.ok) throw new Error("bad store info");
        const info = await r.json();
        return info;
      } catch {
        return { name, model: "?", count: 0 };
      }
    })
  );

  return infos;
}

async function fetchModels() {
  const res = await fetch(`${API_BASE}/models/local`, { cache: "no-store" });
  if (!res.ok) return [];
  const data = (await res.json()) as { local_models: string[] };
  return data.local_models;
}

export default async function StoresPage() {
  const [stores, models] = await Promise.all([fetchStores(), fetchModels()]);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Stores</h1>
        <Suspense fallback={null}>
          <StoresClient models={models} />
        </Suspense>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {stores.map((s) => (
          <Card key={s.name} className="hover:shadow-md transition">
            <CardHeader>
              <CardTitle>{s.name}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm space-y-2">
              <p>Model: <span className="font-mono">{s.model}</span></p>
              <p>Entries: {s.count}</p>
              <Button asChild variant="outline" size="sm">
                <Link href={`/stores/${s.name}`}>Open</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

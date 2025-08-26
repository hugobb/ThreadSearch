"use client";

import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { api } from "@/lib/api";

type SearchResult = {
  id: string;
  text: string;
  score: number;
};

export default function SearchPage() {
  const [stores, setStores] = useState<string[]>([]);
  const [store, setStore] = useState<string>("");
  const [query, setQuery] = useState("");
  const [k, setK] = useState(5);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  // Fetch available stores on mount
  useEffect(() => {
    api<{ stores: string[] }>("/stores/list")
      .then((res) => {
        setStores(res.stores);
        if (res.stores.length > 0) setStore(res.stores[0]);
      })
      .catch((err) => console.error("Failed to load stores", err));
  }, []);

  const runSearch = async () => {
    if (!store || !query.trim()) return;
    setLoading(true);
    try {
      const res = await api<{ results: SearchResult[] }>("/search", {
        method: "POST",
        body: JSON.stringify({ store, query, k }),
      });
      setResults(res.results);
    } catch (err) {
      console.error("Search failed", err);
      alert("Search failed. Check backend logs.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Semantic Search</h1>

      {/* Controls */}
      <div className="flex gap-4 items-end">
        <div className="w-64">
          <label className="text-sm font-medium">Store</label>
          <Select value={store} onValueChange={setStore}>
            <SelectTrigger>
              <SelectValue placeholder="Select a store" />
            </SelectTrigger>
            <SelectContent>
              {stores.map((s) => (
                <SelectItem key={s} value={s}>{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex-1">
          <label className="text-sm font-medium">Query</label>
          <Input
            placeholder="Enter search query…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>

        <div className="w-24">
          <label className="text-sm font-medium">Top-K</label>
          <Input
            type="number"
            min={1}
            value={k}
            onChange={(e) => setK(Number(e.target.value))}
          />
        </div>

        <Button onClick={runSearch} disabled={loading || !store || !query.trim()}>
          {loading ? "Searching…" : "Search"}
        </Button>
      </div>

      {/* Results */}
      <Card>
        <CardHeader>
          <CardTitle>Results</CardTitle>
        </CardHeader>
        <CardContent>
          {results.length === 0 && !loading && (
            <p className="text-sm text-muted-foreground">No results yet. Try a query.</p>
          )}
          <div className="space-y-2">
            {results.map((r, i) => (
              <div key={r.id} className="border p-2 rounded">
                <div className="text-xs text-gray-500">
                  Rank #{i + 1} — Score: {r.score.toFixed(4)}
                </div>
                <div>{r.text}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

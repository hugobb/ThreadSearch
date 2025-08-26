"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Download, HardDrive } from "lucide-react";
import { api } from "@/lib/api";
import type { ModelInfo } from "./types";

type Props = {
  catalog: ModelInfo[];
  localModels: string[];
};

export function ModelBrowserClient({ catalog, localModels }: Props) {
  const [query, setQuery] = useState("");
  const [onlyLocal, setOnlyLocal] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [local, setLocal] = useState<string[]>(localModels);

  const isLocal = (repo: string) => local.includes(repo);

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    return catalog.filter((m) => {
      const matches = m.name.toLowerCase().includes(q) || m.repo.toLowerCase().includes(q);
      const keep = !onlyLocal || isLocal(m.repo);
      return matches && keep;
    });
  }, [catalog, query, onlyLocal, local]);

  const refreshLocal = async () => {
    try {
      const res = await api<{ local_models: string[] }>("/models/local");
      setLocal(res.local_models);
    } catch {
      // ignore
    }
  };

  const downloadModel = async (m: ModelInfo) => {
    setDownloading(m.id);
    try {
      await api("/models/download", {
        method: "POST",
        body: JSON.stringify({ repo_id: m.id }),
      });
      await refreshLocal();
    } catch (err) {
      console.error("Download failed", err);
      alert("Download failed. Check backend logs.");
    } finally {
      setDownloading(null);
    }
  };

  return (
    <>
      {/* Search + Filter */}
      <div className="flex items-center gap-4">
        <Input
          placeholder="Search models…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-80"
        />
        <div className="flex items-center space-x-2">
          <Checkbox
            id="localOnly"
            checked={onlyLocal}
            onCheckedChange={(v) => setOnlyLocal(Boolean(v))}
          />
          <label htmlFor="localOnly" className="text-sm">Only show local</label>
        </div>
      </div>

      {/* Model grid */}
      <div className="grid gap-6 md:grid-cols-3">
        {filtered.map((m) => {
          const local = isLocal(m.repo);
          return (
            <Card key={m.id} className="flex flex-col">
              <CardHeader>
                <CardTitle>{m.name}</CardTitle>
                <CardDescription>{m.description}</CardDescription>
              </CardHeader>
              <CardContent className="mt-auto flex justify-between items-center">
                <div className="text-xs text-muted-foreground">
                  {local ? (
                    <span className="flex items-center gap-1">
                      <HardDrive size={14} /> Local
                    </span>
                  ) : (
                    "Not downloaded"
                  )}
                </div>
                <div className="flex gap-2">
                  {!local && (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={downloading === m.id}
                      onClick={() => downloadModel(m)}
                    >
                      {downloading === m.id ? "Downloading…" : (
                        <>
                          <Download className="w-4 h-4 mr-1" /> Download
                        </>
                      )}
                    </Button>
                  )}
                  <Button size="sm" asChild>
                    <Link href={`/model/${encodeURIComponent(m.id)}`}>Details</Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </>
  );
}

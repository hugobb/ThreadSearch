"use client";

import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";

type Entry = { id: string; text: string };
type Job = {
  id: string;
  filename: string;
  store: string;
  status: "pending" | "processing" | "done" | "failed";
  progress: number;
  logs: string[];
  error: string | null;
};

export default function StoreClient({ store, initialEntries }: { store: string; initialEntries: Entry[] }) {
  const [query, setQuery] = useState("");
  const [k, setK] = useState(5);
  const [results, setResults] = useState<any[]>([]);
  const [loadingSearch, setLoadingSearch] = useState(false); // 🔑 new state
  const [newText, setNewText] = useState("");
  const [entries, setEntries] = useState<Entry[]>(initialEntries);

  const [loadingAdd, setLoadingAdd] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [batchSize, setBatchSize] = useState(64);

  const [jobs, setJobs] = useState<Record<string, Job>>({});
  const [deleteOpen, setDeleteOpen] = useState(false);

  // WebSocket jobs API
  useEffect(() => {
    const ws = new WebSocket(`${process.env.NEXT_PUBLIC_API_BASE_WS}/ws/jobs`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "job_update") {
        const job = data.job as Job;
        if (job.store === store) {
          setJobs((prev) => ({ ...prev, [job.id]: job }));
          if (job.status === "done") {
            api<{ entries: Entry[] }>(`/stores/${store}/entries`).then((res) => {
              setEntries(res.entries);
            });
          }
        }
      }
    };
    return () => ws.close();
  }, [store]);

  const runSearch = async () => {
    if (!query.trim()) return;
    setLoadingSearch(true);
    try {
      const res = await api<{ results: any[] }>("/search", {
        method: "POST",
        body: JSON.stringify({ store, query, k }),
      });
      setResults(res.results);
    } finally {
      setLoadingSearch(false);
    }
  };

  const addManual = async () => {
    if (!newText.trim()) return;
    setLoadingAdd(true);
    try {
      const res = await api<{ entries: Entry[] }>("/stores/add_texts", {
        method: "POST",
        body: JSON.stringify({ store, texts: [newText.trim()] }),
      });
      setEntries([...entries, ...res.entries]);
      setNewText("");
    } finally {
      setLoadingAdd(false);
    }
  };

  const uploadFile = async () => {
    if (!file) return;
    try {
      const fd = new FormData();
      fd.append("store", store);
      fd.append("file", file);
      fd.append("batch_size", String(batchSize));
      const base = process.env.NEXT_PUBLIC_API_BASE!;
      const res = await fetch(`${base}/stores/upload_file`, { method: "POST", body: fd });
      if (!res.ok) {
        alert(await res.text());
      } else {
        const { job_id } = await res.json();
        console.log("File upload launched job:", job_id);
      }
    } finally {
      setFile(null);
    }
  };

  const deleteEntry = async (id: string) => {
    setDeletingId(id);
    try {
      await api("/stores/delete_text", {
        method: "POST",
        body: JSON.stringify({ store, id }),
      });
      setEntries(entries.filter((e) => e.id !== id));
    } finally {
      setDeletingId(null);
    }
  };

  const deleteStore = async () => {
    try {
      await api(`/stores/delete/${store}`, { method: "POST" });
      window.location.href = "/stores";
    } catch {
      alert("Failed to delete store.");
    } finally {
      setDeleteOpen(false);
    }
  };

  const storeJobs = Object.values(jobs).sort(
    (a, b) => new Date(b.id).getTime() - new Date(a.id).getTime()
  );

  return (
    <>
      {/* Store actions */}
      <div className="flex justify-end">
        <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
          <DialogTrigger asChild>
            <Button variant="destructive">Delete Store</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete Store</DialogTitle>
            </DialogHeader>
            <p className="text-sm">Are you sure you want to delete this store and all its entries?</p>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteOpen(false)}>Cancel</Button>
              <Button variant="destructive" onClick={deleteStore}>Delete</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Entries */}
      <Card>
        <CardHeader><CardTitle>Entries</CardTitle></CardHeader>
        <CardContent>
          <div className="max-h-64 overflow-y-auto border rounded p-2 space-y-2 text-sm">
            {entries.length === 0 && <p className="text-muted-foreground">No entries yet</p>}
            {entries.map((e) => (
              <div key={e.id} className="border p-2 rounded flex justify-between items-start">
                <div>
                  <div className="text-xs text-gray-500">{e.id}</div>
                  <div>{e.text}</div>
                </div>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => deleteEntry(e.id)}
                  disabled={deletingId === e.id}
                >
                  {deletingId === e.id ? "Deleting…" : "Delete"}
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Search */}
      <Card>
        <CardHeader><CardTitle>Search (Embeddings)</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter search query…"
            />
            <Input
              type="number"
              min={1}
              value={k}
              onChange={(e) => setK(Number(e.target.value))}
              className="w-20"
            />
            <Button onClick={runSearch} disabled={loadingSearch}>
              {loadingSearch ? "Searching…" : "Search"}
            </Button>
          </div>

          {loadingSearch && (
            <div className="text-sm text-muted-foreground mt-2">Searching, please wait…</div>
          )}

          {!loadingSearch && results.length === 0 && query && (
            <div className="text-sm text-muted-foreground mt-2">No results found.</div>
          )}

          <div className="space-y-2">
            {results.map((r, i) => (
              <div key={i} className="border p-2 rounded">
                <div className="text-xs text-gray-500">score: {r.score.toFixed(4)}</div>
                <div>{r.text}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Add data */}
      <Card>
        <CardHeader><CardTitle>Add Data</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <Textarea
            value={newText}
            onChange={(e) => setNewText(e.target.value)}
            placeholder="Enter text…"
          />
          <Button onClick={addManual} disabled={loadingAdd}>
            {loadingAdd ? "Adding…" : "Add Text"}
          </Button>

          <div className="flex gap-2 items-center">
            <Input
              type="file"
              accept=".txt"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="flex-1"
            />
            <Input
              type="number"
              min={1}
              value={batchSize}
              onChange={(e) => setBatchSize(Number(e.target.value))}
              className="w-24"
            />
            <Button onClick={uploadFile} disabled={!file}>
              Upload
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Jobs */}
      {storeJobs.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Background Jobs</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {storeJobs.map((job) => (
              <div key={job.id} className="border p-2 rounded">
                <div className="flex justify-between items-center">
                  <span className="font-medium">{job.filename}</span>
                  <span className="text-xs">{job.status}</span>
                </div>
                <Progress value={job.status === "done" ? 100 : job.progress} className="mt-1" />
                {job.error && <div className="text-red-500 text-xs mt-1">Error: {job.error}</div>}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </>
  );
}

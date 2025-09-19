"use client";

import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { api } from "@/lib/api";

type PathResult = {
    nodes: { id: string; text: string }[];
    distance: number;
};

export default function GraphSearchPage() {
    const [stores, setStores] = useState<string[]>([]);
    const [store, setStore] = useState("");
    const [start, setStart] = useState("");
    const [end, setEnd] = useState("");
    const [k, setK] = useState(5);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<PathResult | null>(null);

    // Load available stores
    useEffect(() => {
        api<{ stores: string[] }>("/stores/list")
            .then((res) => {
                setStores(res.stores);
                if (res.stores.length > 0) setStore(res.stores[0]);
            })
            .catch((err) => console.error("Failed to load stores", err));
    }, []);

    const runGraphSearch = async () => {
        if (!store || !start.trim() || !end.trim()) return;
        setLoading(true);
        setResult(null);

        try {
            const res = await api<PathResult>("/graph_search", {
                method: "POST",
                body: JSON.stringify({ store, start, end, k }),
            });
            setResult(res);
        } catch (err) {
            console.error("Graph search failed", err);
            alert("Graph search failed. Check backend logs.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <h1 className="text-2xl font-bold">Graph Search</h1>

            {/* Controls */}
            <Card>
                <CardHeader>
                    <CardTitle>Parameters</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                    <div className="flex gap-4">
                        <div className="w-64">
                            <label className="text-sm font-medium">Store</label>
                            <Select value={store} onValueChange={setStore}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Select a store" />
                                </SelectTrigger>
                                <SelectContent>
                                    {stores.map((s) => (
                                        <SelectItem key={s} value={s}>
                                            {s}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="flex-1">
                            <label className="text-sm font-medium">Start Sentence</label>
                            <Input value={start} onChange={(e) => setStart(e.target.value)} />
                        </div>
                        <div className="flex-1">
                            <label className="text-sm font-medium">End Sentence</label>
                            <Input value={end} onChange={(e) => setEnd(e.target.value)} />
                        </div>
                        <div className="w-24">
                            <label className="text-sm font-medium">Steps (k)</label>
                            <Input
                                type="number"
                                min={1}
                                value={k}
                                onChange={(e) => setK(Number(e.target.value))}
                            />
                        </div>
                    </div>
                    <Button onClick={runGraphSearch} disabled={loading}>
                        {loading ? "Searching…" : "Find Path"}
                    </Button>
                </CardContent>
            </Card>

            {/* Result */}
            {result && (
                <Card>
                    <CardHeader>
                        <CardTitle>Path</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-sm text-gray-500 mb-2">
                            Path length: {result.nodes.length} — Distance:{" "}
                            {result.distance.toFixed(4)}
                        </p>
                        <ol className="list-decimal ml-5 space-y-1">
                            {result.nodes.map((n) => (
                                <li key={n.id}>
                                    <span className="font-medium">{n.text}</span>{" "}
                                    <span className="text-xs text-gray-400">({n.id})</span>
                                </li>
                            ))}
                        </ol>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}

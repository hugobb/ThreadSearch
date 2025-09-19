"use client";

import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { api } from "@/lib/api";

type InterpolationResult = {
    step: number;
    results: { id: string; text: string; score: number }[];
};

export default function InterpolatePage() {
    const [stores, setStores] = useState<string[]>([]);
    const [store, setStore] = useState<string>("");
    const [sentenceA, setSentenceA] = useState("");
    const [sentenceB, setSentenceB] = useState("");
    const [steps, setSteps] = useState(5);
    const [k, setK] = useState(1);
    const [results, setResults] = useState<InterpolationResult[]>([]);
    const [loading, setLoading] = useState(false);

    // Fetch available stores
    useEffect(() => {
        api<{ stores: string[] }>("/stores/list")
            .then((res) => {
                setStores(res.stores);
                if (res.stores.length > 0) setStore(res.stores[0]);
            })
            .catch((err) => console.error("Failed to load stores", err));
    }, []);

    const runInterpolate = async () => {
        if (!store || !sentenceA.trim() || !sentenceB.trim()) return;
        setLoading(true);
        try {
            const res = await api<{ interpolations: InterpolationResult[] }>("/interpolate", {
                method: "POST",
                body: JSON.stringify({
                    store,
                    sentence_a: sentenceA,
                    sentence_b: sentenceB,
                    steps,
                    k,
                }),
            });
            setResults(res.interpolations);
        } catch (err) {
            console.error("Interpolation failed", err);
            alert("Interpolation failed. Check backend logs.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            <h1 className="text-2xl font-bold">Sentence Interpolation</h1>

            {/* Controls */}
            <Card>
                <CardHeader>
                    <CardTitle>Inputs</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
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

                    <div>
                        <label className="text-sm font-medium">Sentence A</label>
                        <Input
                            placeholder="Enter first sentence"
                            value={sentenceA}
                            onChange={(e) => setSentenceA(e.target.value)}
                        />
                    </div>

                    <div>
                        <label className="text-sm font-medium">Sentence B</label>
                        <Input
                            placeholder="Enter second sentence"
                            value={sentenceB}
                            onChange={(e) => setSentenceB(e.target.value)}
                        />
                    </div>

                    <div className="flex gap-4">
                        <div className="w-24">
                            <label className="text-sm font-medium">Steps</label>
                            <Input
                                type="number"
                                min={1}
                                value={steps}
                                onChange={(e) => setSteps(Number(e.target.value))}
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
                    </div>

                    <Button
                        onClick={runInterpolate}
                        disabled={loading || !store || !sentenceA.trim() || !sentenceB.trim()}
                    >
                        {loading ? "Interpolating…" : "Run Interpolation"}
                    </Button>
                </CardContent>
            </Card>

            {/* Results */}
            {results.length > 0 && (
                <Card>
                    <CardHeader>
                        <CardTitle>Results</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {results.map((step) => (
                            <div key={step.step} className="border p-2 rounded">
                                <p className="font-medium">Step {step.step}</p>
                                {step.results.map((r, i) => (
                                    <div key={i}>
                                        <div className="text-xs text-gray-500">
                                            score: {r.score.toFixed(4)}
                                        </div>
                                        <div>{r.text}</div>
                                    </div>
                                ))}
                            </div>
                        ))}
                    </CardContent>
                </Card>
            )}
        </div>
    );
}

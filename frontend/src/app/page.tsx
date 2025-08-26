"use client";
import Link from "next/link";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Search, Database, Cpu } from "lucide-react";

export default function Home() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Welcome to TinyFind 🔎</h1>
      <p className="text-muted-foreground">
        A local-first app to embed text with any Hugging Face model, store it, and find the
        <span className="font-semibold"> needle in the haystack</span>.
      </p>

      <div className="grid gap-6 md:grid-cols-3">
        {/* Model card */}
        <Card>
          <CardHeader>
            <Cpu className="w-6 h-6 text-muted-foreground" />
            <CardTitle>Download Model</CardTitle>
            <CardDescription>Download Hugging Face embedding model, so that you can use them.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full">
              <Link href="/model">Go to Model</Link>
            </Button>
          </CardContent>
        </Card>

        {/* Stores card */}
        <Card>
          <CardHeader>
            <Database className="w-6 h-6 text-muted-foreground" />
            <CardTitle>Manage Stores</CardTitle>
            <CardDescription>Create, load, and add texts to your stores</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full">
              <Link href="/stores">Go to Stores</Link>
            </Button>
          </CardContent>
        </Card>

        {/* Search card */}
        <Card>
          <CardHeader>
            <Search className="w-6 h-6 text-muted-foreground" />
            <CardTitle>Search</CardTitle>
            <CardDescription>Find the closest matches to your query</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full">
              <Link href="/search">Go to Search</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

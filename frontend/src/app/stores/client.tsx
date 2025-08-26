"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";

type Props = {
  models: string[];
};

export default function StoresClient({ models }: Props) {
  const [search, setSearch] = useState("");
  const [newStoreName, setNewStoreName] = useState("");
  const [selectedModel, setSelectedModel] = useState("");
  const [open, setOpen] = useState(false);

  const createStore = async () => {
    if (!newStoreName.trim() || !selectedModel) return;
    await api("/stores/create", {
      method: "POST",
      body: JSON.stringify({ name: newStoreName.trim(), model: selectedModel }),
    });
    setNewStoreName("");
    setSelectedModel("");
    setOpen(false);
    // refresh page after create
    window.location.reload();
  };

  return (
    <div className="flex items-center gap-4">
      <Input
        placeholder="Search stores…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-80"
      />

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <Button>Create Store</Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create a new store</DialogTitle>
          </DialogHeader>

          <div className="space-y-3">
            <div>
              <Label htmlFor="storeName">Store name</Label>
              <Input
                id="storeName"
                placeholder="Store name"
                value={newStoreName}
                onChange={(e) => setNewStoreName(e.target.value)}
              />
            </div>

            <div>
              <Label htmlFor="model">Embedding model</Label>
              <Select value={selectedModel} onValueChange={setSelectedModel}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select a model" />
                </SelectTrigger>
                <SelectContent>
                  {models.map((m) => (
                    <SelectItem key={m} value={m}>
                      {m}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter>
            <Button onClick={createStore} disabled={!newStoreName || !selectedModel}>
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

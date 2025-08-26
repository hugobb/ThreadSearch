import { notFound } from "next/navigation";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function fetchCatalog() {
  const res = await fetch(`${API_BASE}/models/catalog`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch models catalog");
  return res.json() as Promise<{ models: any[] }>;
}

export default async function ModelDetail({ params }: { params: { id: string } }) {
  const modelId = decodeURIComponent(params.id);
  const catalog = await fetchCatalog();
  const model = catalog.models.find((m) => m.id === modelId);

  if (!model) return notFound();

  return (
    <div className="max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle>{model.name}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p>
            <strong>Repo:</strong> {model.repo}
          </p>
          <p>{model.description}</p>
          {model.tags && model.tags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {model.tags.map((t: string) => (
                <span
                  key={t}
                  className="text-xs bg-gray-100 px-2 py-1 rounded"
                >
                  {t}
                </span>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

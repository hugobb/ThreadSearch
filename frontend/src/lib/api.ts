export async function api<T>(path: string, opts?: RequestInit): Promise<T> {
  console.log(`API Request: ${path}`, opts);
  const base = process.env.NEXT_PUBLIC_API_BASE!;
  const res = await fetch(`${base}${path}`, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...(opts?.headers || {}) },
    cache: 'no-store',
  });
  console.log(`API Response: ${path}`, res);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
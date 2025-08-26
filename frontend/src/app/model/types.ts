export type ModelInfo = {
  id: string;          // derived from backend key
  repo: string;
  name: string;
  description: string;
  tags?: string[];
};
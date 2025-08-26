"use client";
import { useEffect, useState } from "react";
import { Progress } from "@/components/ui/progress";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronRight, RotateCcw } from "lucide-react";

type JobLog = {
  timestamp: string;
  message: string;
};

type Job = {
  id: string;
  filename: string;
  status: "pending" | "processing" | "done" | "failed";
  progress: number;
  logs: JobLog[];      // ✅ now structured logs
  error: string | null;
  created_at: string;
  updated_at: string;
};

export default function JobTracker() {
  const [jobs, setJobs] = useState<Record<string, Job>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  useEffect(() => {
    // fetch initial snapshot
    const fetchJobs = async () => {
      try {
        const base = process.env.NEXT_PUBLIC_API_BASE!;
        const res = await fetch(`${base}/jobs`);
        const data = await res.json();
        const jobMap: Record<string, Job> = {};
        data.jobs.forEach((j: Job) => {
          jobMap[j.id] = j;
        });
        setJobs(jobMap);
      } catch (err) {
        console.error("Failed to fetch jobs", err);
      }
    };
    fetchJobs();

    // subscribe via websocket
    const ws = new WebSocket(`${process.env.NEXT_PUBLIC_API_BASE_WS}/ws/jobs`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "job_update") {
        setJobs((prev) => ({ ...prev, [data.job.id]: data.job }));
      }
    };
    ws.onclose = () => console.warn("Job WebSocket closed");

    return () => ws.close();
  }, []);


  const toggleLogs = (id: string) => {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const statusColor = (status: Job["status"]) => {
    switch (status) {
      case "pending":
        return "bg-gray-200 text-gray-700";
      case "processing":
        return "bg-blue-100 text-blue-700";
      case "done":
        return "bg-green-100 text-green-700";
      case "failed":
        return "bg-red-100 text-red-700";
    }
  };

  const jobList = Object.values(jobs);
  const running = jobList.filter((j) => j.status === "processing");
  const waiting = jobList.filter((j) => j.status === "pending");
  const completed = jobList.filter((j) => j.status === "done" || j.status === "failed");

  const sortByTime = (a: Job, b: Job) =>
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime();

  running.sort(sortByTime);
  waiting.sort(sortByTime);
  completed.sort(sortByTime);

  const renderJobCard = (job: Job) => (
    <Card key={job.id} className="p-3 space-y-2">
      <div className="flex justify-between items-center">
        <div>
          <p className="font-medium">{job.filename}</p>
          <Badge className={statusColor(job.status)}>{job.status}</Badge>
        </div>
        {job.status === "failed" && (
          <Button variant="destructive" size="sm">
            <RotateCcw className="w-4 h-4 mr-1" /> Retry
          </Button>
        )}
      </div>

      <Progress value={job.status === "done" ? 100 : job.progress} />

      {(job.error || job.logs.length > 0) && (
        <div>
          <Button
            variant="ghost"
            size="sm"
            className="flex items-center gap-1"
            onClick={() => toggleLogs(job.id)}
          >
            {expanded[job.id] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            Logs
          </Button>
          {expanded[job.id] && (
            <div className="mt-1 bg-gray-50 p-2 rounded text-xs max-h-40 overflow-y-auto space-y-1">
              {job.error && (
                <div className="text-red-600 font-semibold">Error: {job.error}</div>
              )}
              {job.logs.map((log, i) => (
                <div key={i} className="flex gap-2">
                  <span className="text-gray-500 whitespace-nowrap">
                    [{new Date(log.timestamp).toLocaleTimeString()}]
                  </span>
                  <span>{log.message}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </Card>
  );

  return (
    <div className="space-y-8">
      {/* Running */}
      <section>
        <h2 className="text-lg font-bold mb-2">Running</h2>
        {running.length === 0 ? (
          <p className="text-sm text-muted-foreground">No jobs currently running.</p>
        ) : (
          <div className="space-y-3">{running.map(renderJobCard)}</div>
        )}
      </section>

      {/* Waiting */}
      <section>
        <h2 className="text-lg font-bold mb-2">Waiting</h2>
        {waiting.length === 0 ? (
          <p className="text-sm text-muted-foreground">No jobs waiting in queue.</p>
        ) : (
          <div className="space-y-3">{waiting.map(renderJobCard)}</div>
        )}
      </section>

      {/* Completed */}
      <section>
        <h2 className="text-lg font-bold mb-2">Completed</h2>
        {completed.length === 0 ? (
          <p className="text-sm text-muted-foreground">No completed jobs yet.</p>
        ) : (
          <div className="max-h-64 overflow-y-auto space-y-3 border rounded p-2">
            {completed.map(renderJobCard)}
          </div>
        )}
      </section>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { ScrollText, Filter, CheckCircle2, AlertTriangle, Clock } from "lucide-react";
import { api } from "@/lib/api";

export default function AuditPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadLogs() {
      try {
        setLoading(true);
        const res = await api.audit.getLogs();
        setLogs(res || []);
      } catch (e) {
        console.warn("Could not load audit logs:", e);
      } finally {
        setLoading(false);
      }
    }
    loadLogs();
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <ScrollText className="h-6 w-6 text-emerald-400" />
          <span>Audit Trail & Observability</span>
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Tamper-evident, append-only activity log tracking every model proposal, backend authorization, human approval, and tool execution.
        </p>
      </div>

      <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-4 shadow-xl">
        {loading ? (
          <div className="text-center py-16 text-slate-400 text-xs">Loading audit logs...</div>
        ) : logs.length === 0 ? (
          <div className="text-center py-20 text-slate-500 text-xs">No audit events recorded yet.</div>
        ) : (
          <div className="space-y-3">
            {logs.map((log) => {
              const isSuccess = log.outcome === "success";
              const isPaused = log.outcome === "paused";
              return (
                <div
                  key={log.id}
                  className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 text-xs space-y-2"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                          isSuccess
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : isPaused
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                            : "bg-red-500/10 text-red-400 border border-red-500/20"
                        }`}
                      >
                        {log.outcome}
                      </span>
                      <strong className="text-white capitalize text-sm">
                        {log.action_type?.replace(/_/g, " ")}
                      </strong>
                    </div>
                    <span className="text-[11px] text-slate-500">
                      {new Date(log.timestamp).toLocaleString()}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] text-slate-400 bg-slate-900/50 p-2.5 rounded-lg border border-slate-800/60">
                    <div>Tool: <span className="text-slate-200 font-mono">{log.tool_name || "N/A"}</span></div>
                    <div>Resource: <span className="text-slate-200">{log.resource_type || "N/A"}</span></div>
                    <div>Actor: <span className="text-slate-200">{log.actor_email || "System/Agent"}</span></div>
                    <div>Correlation: <span className="text-slate-400 font-mono">{log.correlation_id?.slice(0, 8)}...</span></div>
                  </div>

                  {log.details_json && Object.keys(log.details_json).length > 0 && (
                    <div className="font-mono text-[10px] text-slate-400 bg-slate-950 p-2 rounded border border-slate-800/80 max-h-24 overflow-y-auto">
                      <pre>{JSON.stringify(log.details_json, null, 2)}</pre>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

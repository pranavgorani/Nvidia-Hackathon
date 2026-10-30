"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Workflow, Play, CheckCircle2, Clock, AlertTriangle, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";

export default function AutomationsPage() {
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadWorkflows() {
      try {
        setLoading(true);
        const res = await api.agent.getWorkflows();
        setWorkflows(res || []);
      } catch (e) {
        console.warn("Could not load workflows:", e);
      } finally {
        setLoading(false);
      }
    }
    loadWorkflows();
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Workflow className="h-6 w-6 text-purple-400" />
            <span>Workflow Automation & Execution History</span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Event-driven triggers, durable state machine executions, and multi-step agent runs.
          </p>
        </div>
        <Link
          href="/workspace"
          className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-purple-500 hover:bg-purple-600 text-slate-950 font-semibold text-xs transition-all"
        >
          <Play className="h-3.5 w-3.5 fill-current" />
          <span>Launch New Workflow</span>
        </Link>
      </div>

      {/* Triggers Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-sm text-white">Document Upload Ingestion Trigger</h3>
            <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-semibold">Enabled</span>
          </div>
          <p className="text-xs text-slate-400">
            Automatically initiates Property Intake Agent when new PDF inquiries or image flyers are uploaded.
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-sm text-white">Follow-up Preparation Schedule</h3>
            <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 font-semibold">Ready</span>
          </div>
          <p className="text-xs text-slate-400">
            Scans leads with pending follow-up dates and pre-drafts tailored communication tasks.
          </p>
        </div>
      </div>

      {/* Workflow Runs Table */}
      <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-4">
        <h3 className="font-bold text-sm text-white">Execution Run History</h3>

        {loading ? (
          <div className="text-center py-12 text-slate-400 text-xs">Loading execution runs...</div>
        ) : workflows.length === 0 ? (
          <div className="text-center py-16 text-slate-500 text-xs">No workflows executed yet.</div>
        ) : (
          <div className="space-y-3">
            {workflows.map((wf) => (
              <div
                key={wf.id}
                className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 text-xs flex flex-col md:flex-row md:items-center justify-between gap-3"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        wf.status === "completed"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : wf.status === "paused_for_approval"
                          ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                          : "bg-red-500/10 text-red-400 border border-red-500/20"
                      }`}
                    >
                      {wf.status}
                    </span>
                    <span className="font-semibold text-slate-200 capitalize">
                      {wf.skill_id?.replace(/_/g, " ")}
                    </span>
                  </div>
                  <p className="text-slate-400 truncate max-w-xl">{wf.initial_instruction}</p>
                </div>

                <div className="flex items-center gap-4 text-slate-500 text-[11px]">
                  <span>{new Date(wf.created_at).toLocaleString()}</span>
                  <Link
                    href={`/workspace`}
                    className="text-emerald-400 hover:text-emerald-300 font-medium flex items-center gap-1"
                  >
                    <span>View Timeline</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

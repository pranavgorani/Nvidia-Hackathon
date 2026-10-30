"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Users,
  FileText,
  Building,
  CheckSquare,
  Workflow,
  Sparkles,
  ArrowUpRight,
  ShieldCheck,
  Clock,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileUp
} from "lucide-react";
import { api } from "@/lib/api";

export default function DashboardOverview() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadMetrics() {
      try {
        setLoading(true);
        // Ensure default auth session exists
        try {
          await api.auth.getMe();
        } catch {
          await api.auth.login("admin@docuflow.ai", "DocuFlow2026!");
        }

        const metricsData = await api.dashboard.getMetrics();
        setData(metricsData);
        setError(null);
      } catch (err: any) {
        setError(err.message || "Failed to load dashboard metrics");
      } finally {
        setLoading(false);
      }
    }
    loadMetrics();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
        <p className="text-sm text-slate-400">Loading DocuFlow Agent metrics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 flex items-center gap-3">
        <AlertTriangle className="h-5 w-5" />
        <div>
          <div className="font-semibold">Unable to load metrics</div>
          <div className="text-xs text-red-300">{error}</div>
        </div>
      </div>
    );
  }

  const m = data?.metrics || {};
  const recentActivities = data?.recent_activities || [];
  const aiProvider = data?.ai_provider || {};

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-850 to-slate-900 border border-slate-800 shadow-xl">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              SaaS2Agent Hackathon Track
            </span>
            <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
              PS 2: Best Apps & Agents
            </span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">DocuFlow AI Agent OS</h1>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Autonomous document intelligence converting real estate inquiries into validated CRM records with human approvals and verified audit logs.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/workspace"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold text-sm transition-all shadow-lg shadow-emerald-500/20"
          >
            <Sparkles className="h-4 w-4 fill-current" />
            <span>Open Agent Workspace</span>
          </Link>
          <Link
            href="/documents"
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-sm border border-slate-700 transition-all"
          >
            <FileUp className="h-4 w-4 text-slate-400" />
            <span>Upload Document</span>
          </Link>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Total CRM Leads</span>
            <Users className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">{m.total_leads || 0}</div>
          <div className="text-[11px] text-slate-400 mt-1">
            <span className="text-emerald-400 font-semibold">{m.new_inquiries || 0}</span> new inquiries
          </div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Documents Processed</span>
            <FileText className="h-4 w-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">{m.documents_processed || 0}</div>
          <div className="text-[11px] text-slate-400 mt-1">With field evidence & confidence</div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Pending Approvals</span>
            <CheckSquare className="h-4 w-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400 mt-2">{m.pending_approvals || 0}</div>
          <div className="text-[11px] text-slate-400 mt-1">
            {m.pending_approvals > 0 ? (
              <Link href="/approvals" className="text-amber-400 hover:underline">
                Requires human review →
              </Link>
            ) : (
              "All clear"
            )}
          </div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
            <span>Workflows Completed</span>
            <Workflow className="h-4 w-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">{m.completed_workflows || 0}</div>
          <div className="text-[11px] text-slate-400 mt-1">
            Running: <span className="text-blue-400">{m.workflows_running || 0}</span> | Failed:{" "}
            <span className="text-red-400">{m.failed_workflows || 0}</span>
          </div>
        </div>
      </div>

      {/* Main Grid: Active AI Provider & Recent Audit Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Quick Access & Architecture */}
        <div className="lg:col-span-2 space-y-6">
          {/* Signature Skill Feature Card */}
          <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Signature Workflow
                </span>
                <h2 className="text-lg font-bold text-white mt-2">Property Intake Agent (v1.0.0)</h2>
                <p className="text-xs text-slate-400 mt-1">
                  End-to-end 11-step pipeline: document ingestion, PDF OCR/extraction, entity resolution, CRM deduplication, cryptographic approval binding, and verified database persistence.
                </p>
              </div>
              <Link
                href="/workspace"
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 transition-colors"
              >
                Launch Skill
              </Link>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 text-xs">
              <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60">
                <div className="text-slate-400 font-medium">Step 1-3</div>
                <div className="font-semibold text-slate-200 mt-0.5">Ingest & Extract</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60">
                <div className="text-slate-400 font-medium">Step 4-5</div>
                <div className="font-semibold text-slate-200 mt-0.5">Validate & Match</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60">
                <div className="text-slate-400 font-medium">Step 6-8</div>
                <div className="font-semibold text-amber-400 mt-0.5">Human Approval</div>
              </div>
              <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60">
                <div className="text-slate-400 font-medium">Step 9-11</div>
                <div className="font-semibold text-emerald-400 mt-0.5">Execute & Verify</div>
              </div>
            </div>
          </div>

          {/* Infrastructure Disclosure Card */}
          <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/90 space-y-3">
            <div className="flex items-center gap-2 text-sm font-semibold text-white">
              <ShieldCheck className="h-5 w-5 text-emerald-400" />
              <span>AI Provider & Technology Disclosure</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              DocuFlow AI Agent OS is fully integrated with the <span className="text-slate-200 font-semibold">Google Gemini API</span> using the official supported <code className="text-emerald-400 bg-emerald-950/60 px-1 py-0.5 rounded">google-genai</code> Python SDK. The active model is <span className="text-slate-200 font-mono font-medium">{aiProvider.model}</span>. All model requests pass strictly through the backend with zero-trust tool execution.
            </p>
            <div className="flex flex-wrap gap-2 pt-1 text-[11px]">
              <span className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300">
                Provider: <span className="text-emerald-400 font-mono">{aiProvider.name}</span>
              </span>
              <span className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300">
                Architecture: <span className="text-slate-200">Server-Side Only</span>
              </span>
              <span className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300">
                Tool Calling: <span className="text-emerald-400">Strict Backend Allowlist</span>
              </span>
            </div>
          </div>
        </div>

        {/* Right Column: Activity / Audit Trail */}
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Clock className="h-4 w-4 text-emerald-400" />
              <span>Recent Activity Feed</span>
            </h3>
            <Link href="/audit" className="text-xs text-slate-400 hover:text-emerald-400">
              View all →
            </Link>
          </div>

          {recentActivities.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-500">
              No activity logged yet. Run a workflow or upload a document to view audit events.
            </div>
          ) : (
            <div className="space-y-3">
              {recentActivities.slice(0, 6).map((item: any) => {
                const isSuccess = item.outcome === "success";
                const isPaused = item.outcome === "paused";
                return (
                  <div key={item.id} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/60 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-200 truncate capitalize">
                        {item.action_type?.replace(/_/g, " ")}
                      </span>
                      <span
                        className={`text-[10px] px-1.5 py-0.2 rounded font-medium ${
                          isSuccess
                            ? "bg-emerald-500/10 text-emerald-400"
                            : isPaused
                            ? "bg-amber-500/10 text-amber-400"
                            : "bg-red-500/10 text-red-400"
                        }`}
                      >
                        {item.outcome}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 flex items-center justify-between">
                      <span>Tool: {item.tool_name || "Agent"}</span>
                      <span className="text-[10px] text-slate-500">
                        {new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

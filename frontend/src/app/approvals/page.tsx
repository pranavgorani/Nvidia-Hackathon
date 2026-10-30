"use client";

import { useEffect, useState } from "react";
import {
  CheckSquare,
  CheckCircle2,
  XCircle,
  Clock,
  ShieldCheck,
  AlertTriangle,
  ChevronRight,
  Filter
} from "lucide-react";
import { api } from "@/lib/api";

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState("pending");
  const [decidingId, setDecidingId] = useState<string | null>(null);

  async function loadApprovals() {
    try {
      setLoading(true);
      const res = await api.approvals.list(filterStatus === "all" ? undefined : filterStatus);
      setApprovals(res || []);
    } catch (e) {
      console.warn("Could not load approvals:", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadApprovals();
  }, [filterStatus]);

  async function handleDecide(id: string, decision: "approve" | "reject") {
    try {
      setDecidingId(id);
      await api.approvals.decide(id, decision, `Action ${decision}d via Approval Center`);
      await loadApprovals();
    } catch (err: any) {
      alert(`Approval decision failed: ${err.message}`);
    } finally {
      setDecidingId(null);
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <CheckSquare className="h-6 w-6 text-amber-400" />
            <span>Human Approval Center</span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Cryptographically bound authorization for consequential CRM mutations with SHA-256 payload verification.
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1 bg-slate-900/60 p-1.5 rounded-xl border border-slate-800">
          {["all", "pending", "completed", "rejected"].map((st) => (
            <button
              key={st}
              onClick={() => setFilterStatus(st)}
              className={`px-3 py-1 rounded-lg text-xs font-medium capitalize transition-colors ${
                filterStatus === st
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-center py-16 text-slate-400 text-xs">Loading approvals...</div>
      ) : approvals.length === 0 ? (
        <div className="text-center py-20 rounded-2xl bg-slate-900/40 border border-slate-800 text-slate-500 text-xs">
          No approval requests found in status '{filterStatus}'.
        </div>
      ) : (
        <div className="space-y-4">
          {approvals.map((appr) => {
            const isPending = appr.status === "pending";
            return (
              <div
                key={appr.id}
                className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-4 shadow-lg"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800/80">
                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider ${
                        isPending
                          ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                          : appr.status === "completed"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : "bg-red-500/10 text-red-400 border border-red-500/20"
                      }`}
                    >
                      {appr.status}
                    </span>
                    <h3 className="text-sm font-bold text-white capitalize">
                      {appr.proposed_action?.replace(/_/g, " ")}
                    </h3>
                  </div>

                  <div className="flex items-center gap-3 text-xs text-slate-400">
                    <span className="font-mono text-[11px]">
                      Payload Hash: <strong className="text-slate-200">{appr.payload_hash?.slice(0, 16)}...</strong>
                    </span>
                    <span>Expires: {new Date(appr.expires_at).toLocaleDateString()}</span>
                  </div>
                </div>

                {/* Proposed Payload Box */}
                <div className="space-y-1.5">
                  <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    Proposed CRM Action Payload (Verified)
                  </div>
                  <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800/80 font-mono text-xs text-slate-300 overflow-x-auto max-h-48">
                    {JSON.stringify(appr.proposed_payload_json, null, 2)}
                  </pre>
                </div>

                {/* Execution Result if completed */}
                {appr.execution_result_json && (
                  <div className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-800/30 text-xs text-emerald-300">
                    <div className="font-semibold mb-1">Execution Outcome:</div>
                    <pre className="font-mono text-[11px] text-emerald-400/90">
                      {JSON.stringify(appr.execution_result_json, null, 2)}
                    </pre>
                  </div>
                )}

                {/* Decision Actions */}
                {isPending && (
                  <div className="flex items-center gap-3 pt-2">
                    <button
                      onClick={() => handleDecide(appr.id, "approve")}
                      disabled={decidingId === appr.id}
                      className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition-all shadow-md shadow-emerald-500/20"
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      <span>{decidingId === appr.id ? "Authorizing..." : "Approve & Execute Mutation"}</span>
                    </button>
                    <button
                      onClick={() => handleDecide(appr.id, "reject")}
                      disabled={decidingId === appr.id}
                      className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-red-400 font-semibold text-xs border border-slate-700 transition-all"
                    >
                      <span>Reject Action</span>
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

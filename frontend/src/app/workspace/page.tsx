"use client";

import { useEffect, useState } from "react";
import {
  Bot,
  Send,
  FileText,
  Sparkles,
  CheckCircle,
  Clock,
  AlertCircle,
  CheckSquare,
  ShieldCheck,
  ChevronRight,
  Upload,
  RefreshCw
} from "lucide-react";
import { api } from "@/lib/api";

export default function AgentWorkspacePage() {
  const [instruction, setInstruction] = useState("Process this new property inquiry and prepare the CRM update.");
  const [selectedSkill, setSelectedSkill] = useState("property_intake_agent");
  const [documents, setDocuments] = useState<any[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>("");
  const [running, setRunning] = useState(false);
  const [workflowResult, setWorkflowResult] = useState<any>(null);
  const [timelineSteps, setTimelineSteps] = useState<any[]>([]);
  const [pendingApproval, setPendingApproval] = useState<any>(null);
  const [deciding, setDeciding] = useState(false);

  useEffect(() => {
    async function loadDocs() {
      try {
        const docs = await api.documents.list();
        setDocuments(docs || []);
        if (docs && docs.length > 0) {
          setSelectedDocId(docs[0].id);
        }
      } catch (e) {
        console.warn("Could not load documents:", e);
      }
    }
    loadDocs();
  }, []);

  async function handleRun() {
    if (!instruction.trim()) return;
    try {
      setRunning(true);
      setWorkflowResult(null);
      setPendingApproval(null);

      const res = await api.agent.run(
        instruction,
        selectedSkill,
        selectedDocId || undefined
      );

      setWorkflowResult(res);

      // Load timeline steps if workflow_id returned
      if (res.workflow_id) {
        const wfData = await api.agent.getWorkflow(res.workflow_id);
        setTimelineSteps(wfData.steps || []);
      }

      // Check if paused for approval
      if (res.status === "paused_for_approval" && res.approval_id) {
        const appr = await api.approvals.get(res.approval_id);
        setPendingApproval(appr);
      }
    } catch (err: any) {
      alert(`Agent execution error: ${err.message}`);
    } finally {
      setRunning(false);
    }
  }

  async function handleDecideApproval(decision: "approve" | "reject") {
    if (!pendingApproval) return;
    try {
      setDeciding(true);
      const res = await api.approvals.decide(
        pendingApproval.id,
        decision,
        `Decided via Agent Workspace`
      );

      // Reload workflow timeline
      if (workflowResult?.workflow_id) {
        const wfData = await api.agent.getWorkflow(workflowResult.workflow_id);
        setTimelineSteps(wfData.steps || []);
        setWorkflowResult((prev: any) => ({ ...prev, status: wfData.workflow.status, final_summary: wfData.workflow.final_summary }));
      }

      setPendingApproval(null);
    } catch (err: any) {
      alert(`Approval decision failed: ${err.message}`);
    } finally {
      setDeciding(false);
    }
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Bot className="h-6 w-6 text-emerald-400" />
            <span>Agent Workspace</span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Execute agent skills, review model-proposed tool calls, and authorize human-in-the-loop CRM operations.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
          <ShieldCheck className="h-4 w-4 text-emerald-400" />
          <span>Zero-Trust Tool Execution Enabled</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Instruction & Inputs */}
        <div className="space-y-4">
          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-4">
            <div className="font-semibold text-sm text-white flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-emerald-400" />
              <span>Skill & Context Configuration</span>
            </div>

            {/* Skill Selector */}
            <div>
              <label className="text-xs text-slate-400 font-medium mb-1.5 block">Select Agent Skill</label>
              <select
                value={selectedSkill}
                onChange={(e) => setSelectedSkill(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
              >
                <option value="property_intake_agent">Property Intake Agent (Signature Skill)</option>
                <option value="lead_qualification">Lead Qualification</option>
                <option value="document_analyst">Document Analyst</option>
                <option value="follow_up_preparation">Follow-up Preparation</option>
                <option value="crm_record_matching">CRM Record Matching</option>
                <option value="task_planner">Task Planner</option>
              </select>
            </div>

            {/* Document Selector */}
            <div>
              <label className="text-xs text-slate-400 font-medium mb-1.5 block">Attach Document Context</label>
              <select
                value={selectedDocId}
                onChange={(e) => setSelectedDocId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
              >
                <option value="">No document attached (General Instruction)</option>
                {documents.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.original_name} ({d.processing_status})
                  </option>
                ))}
              </select>
            </div>

            {/* Instruction TextArea */}
            <div>
              <label className="text-xs text-slate-400 font-medium mb-1.5 block">User Instruction</label>
              <textarea
                rows={4}
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                placeholder="Instruct the agent on what to process..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 placeholder:text-slate-600 resize-none"
              />
            </div>

            {/* Submit Button */}
            <button
              onClick={handleRun}
              disabled={running}
              className="w-full py-2.5 px-4 rounded-xl bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-slate-950 font-semibold text-xs flex items-center justify-center gap-2 transition-all shadow-md shadow-emerald-500/20"
            >
              {running ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span>Agent Executing...</span>
                </>
              ) : (
                <>
                  <Send className="h-4 w-4" />
                  <span>Execute Workflow</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right Column (2 Cols): Execution Timeline & Approval Center */}
        <div className="lg:col-span-2 space-y-6">
          {/* Pending Approval Card if present */}
          {pendingApproval && (
            <div className="p-6 rounded-2xl bg-amber-500/10 border border-amber-500/30 space-y-4 shadow-xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <CheckSquare className="h-5 w-5 text-amber-400" />
                  <span className="font-bold text-sm text-amber-200">Human Approval Required</span>
                </div>
                <span className="text-[11px] font-mono text-slate-400 bg-slate-950/80 px-2 py-0.5 rounded border border-slate-800">
                  Hash: {pendingApproval.payload_hash?.slice(0, 12)}...
                </span>
              </div>

              <p className="text-xs text-slate-300">
                The agent proposed a CRM write action: <strong className="text-white capitalize">{pendingApproval.proposed_action?.replace(/_/g, " ")}</strong>. Review the verified proposed payload below.
              </p>

              <div className="bg-slate-950/90 rounded-xl p-4 border border-slate-800/80 font-mono text-xs text-slate-300 overflow-x-auto max-h-48">
                <pre>{JSON.stringify(pendingApproval.proposed_payload_json, null, 2)}</pre>
              </div>

              <div className="flex items-center gap-3 pt-2">
                <button
                  onClick={() => handleDecideApproval("approve")}
                  disabled={deciding}
                  className="px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition-all"
                >
                  <CheckCircle className="h-3.5 w-3.5" />
                  <span>Approve & Execute</span>
                </button>
                <button
                  onClick={() => handleDecideApproval("reject")}
                  disabled={deciding}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-red-400 font-semibold text-xs transition-all border border-slate-700"
                >
                  <span>Reject Action</span>
                </button>
              </div>
            </div>
          )}

          {/* Workflow Execution Summary */}
          {workflowResult && (
            <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white">Status:</span>
                  <span
                    className={`px-2 py-0.5 rounded font-semibold text-[11px] uppercase ${
                      workflowResult.status === "completed"
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : workflowResult.status === "paused_for_approval"
                        ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        : "bg-red-500/10 text-red-400 border border-red-500/20"
                    }`}
                  >
                    {workflowResult.status}
                  </span>
                </div>
                <span className="text-slate-500 text-[11px]">Workflow ID: {workflowResult.workflow_id}</span>
              </div>

              {workflowResult.final_summary && (
                <div className="text-xs text-slate-300 bg-slate-950/60 p-3 rounded-lg border border-slate-800/60 whitespace-pre-wrap leading-relaxed">
                  {workflowResult.final_summary}
                </div>
              )}
            </div>
          )}

          {/* Timeline Steps */}
          <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-4">
            <h3 className="font-bold text-sm text-white flex items-center gap-2">
              <Clock className="h-4 w-4 text-emerald-400" />
              <span>Workflow Execution Timeline</span>
            </h3>

            {timelineSteps.length === 0 ? (
              <div className="text-center py-12 text-slate-500 text-xs">
                No active execution steps. Submit an instruction or select a document to start.
              </div>
            ) : (
              <div className="space-y-4 relative before:absolute before:inset-0 before:left-3 before:w-0.5 before:bg-slate-800">
                {timelineSteps.map((s, idx) => (
                  <div key={idx} className="relative flex items-start gap-3 pl-6">
                    <span className="absolute left-1.5 top-1 h-3.5 w-3.5 rounded-full bg-slate-950 border-2 border-emerald-400" />
                    <div className="flex-1 bg-slate-950/60 rounded-xl p-3 border border-slate-800/60 text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-200 capitalize">
                          Step {s.step_number}: {s.step_type?.replace(/_/g, " ")}
                        </span>
                        <span className="text-[10px] text-slate-500">
                          {new Date(s.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                        </span>
                      </div>
                      <div className="bg-slate-900/80 p-2 rounded text-[11px] font-mono text-slate-400 max-h-32 overflow-y-auto">
                        <pre>{JSON.stringify(s.output_data_json || s.input_data_json, null, 2)}</pre>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

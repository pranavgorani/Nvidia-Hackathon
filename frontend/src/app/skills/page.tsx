"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Sparkles, ArrowRight, Shield, CheckCircle, Wrench } from "lucide-react";
import { api } from "@/lib/api";

export default function SkillsPage() {
  const [skills, setSkills] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadSkills() {
      try {
        setLoading(true);
        const res = await api.skills.list();
        setSkills(res || []);
      } catch (e) {
        console.warn("Could not load skills:", e);
      } finally {
        setLoading(false);
      }
    }
    loadSkills();
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-emerald-400" />
          <span>Skills Registry</span>
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Versioned, reusable agent capabilities with explicit tool allowlists and human-in-the-loop policies.
        </p>
      </div>

      {loading ? (
        <div className="text-center py-16 text-slate-400 text-xs">Loading skills...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {skills.map((skill) => {
            const isSignature = skill.skill_id === "property_intake_agent";
            return (
              <div
                key={skill.id}
                className={`p-6 rounded-2xl border space-y-4 transition-all ${
                  isSignature
                    ? "bg-slate-900/90 border-emerald-500/40 shadow-xl shadow-emerald-500/5"
                    : "bg-slate-900/50 border-slate-800"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    {isSignature && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mb-2 inline-block">
                        Signature Skill
                      </span>
                    )}
                    <h2 className="text-base font-bold text-white">{skill.name}</h2>
                    <span className="text-[11px] font-mono text-slate-400">v{skill.version}</span>
                  </div>

                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300">
                    {skill.is_enabled ? "Active" : "Disabled"}
                  </span>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed">{skill.description}</p>

                {/* Allowed Tools */}
                <div className="space-y-1.5">
                  <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Wrench className="h-3 w-3 text-slate-500" />
                    <span>Permitted Tools Allowlist</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {(skill.allowed_tools_json || []).map((t: string) => (
                      <span
                        key={t}
                        className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-[11px] font-mono text-slate-300"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Footer Action */}
                <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                  <span className="text-[11px] text-slate-500">
                    Policy: {skill.approval_policy_json?.require_approval_for_create ? "Requires Approval for Writes" : "Standard"}
                  </span>
                  <Link
                    href={`/workspace`}
                    className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 hover:text-emerald-300"
                  >
                    <span>Run in Workspace</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

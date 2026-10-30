"use client";

import { useEffect, useState } from "react";
import { Settings, ShieldCheck, Building, Key, AlertTriangle, Cpu } from "lucide-react";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const me = await api.auth.getMe();
        setProfile(me);
      } catch (e) {
        console.warn("Could not load settings:", e);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Settings className="h-6 w-6 text-slate-400" />
          <span>Organization & Technology Settings</span>
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Tenant configuration, AI inference parameters, security boundaries, and infrastructure disclosures.
        </p>
      </div>

      {/* Organization Details */}
      <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-4">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <Building className="h-4 w-4 text-emerald-400" />
          <span>Tenant Context</span>
        </h2>

        <div className="grid grid-cols-2 gap-4 text-xs">
          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-slate-500 block mb-1">Organization Name</span>
            <strong className="text-white text-sm">{profile?.current_organization?.name || "Acme Real Estate Holdings"}</strong>
          </div>
          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-slate-500 block mb-1">Authenticated Role</span>
            <strong className="text-emerald-400 capitalize text-sm">{profile?.current_organization?.role || "Owner"}</strong>
          </div>
        </div>
      </div>

      {/* AI Provider & Infrastructure Disclosure */}
      <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Cpu className="h-4 w-4 text-emerald-400" />
            <span>AI Inference Provider (SaaS2Agent Hackathon Stack)</span>
          </h2>
          <span className="px-2.5 py-0.5 rounded text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            Active: Google Gemini API
          </span>
        </div>

        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-slate-500 block mb-0.5">Inference Provider:</span>
              <strong className="text-slate-200 font-mono">google_gemini</strong>
            </div>
            <div>
              <span className="text-slate-500 block mb-0.5">Model Identifier:</span>
              <strong className="text-emerald-400 font-mono">gemini-2.5-flash</strong>
            </div>
            <div>
              <span className="text-slate-500 block mb-0.5">Official SDK:</span>
              <strong className="text-slate-200 font-mono">google-genai (Python)</strong>
            </div>
            <div>
              <span className="text-slate-500 block mb-0.5">Execution Boundary:</span>
              <strong className="text-slate-200">Backend Server-Side Only</strong>
            </div>
          </div>
        </div>

        {/* Hackathon Disclosure Callout */}
        <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20 text-xs text-blue-200 space-y-1.5 leading-relaxed">
          <div className="font-bold flex items-center gap-1.5 text-blue-300">
            <ShieldCheck className="h-4 w-4" />
            <span>Hackathon Technology Disclosure</span>
          </div>
          <p>
            The DocuFlow AI Agent OS inference integration uses the official <strong className="text-white">Google Gemini API</strong> via the <strong className="text-white">google-genai</strong> SDK. Old providers (NVIDIA Nemotron / Nebius inference) have been replaced with the Google Gemini API architecture.
          </p>
        </div>
      </div>
    </div>
  );
}

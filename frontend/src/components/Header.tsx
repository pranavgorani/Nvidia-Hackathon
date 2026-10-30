"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Sparkles, Building2, User, Activity } from "lucide-react";
import { api } from "@/lib/api";

export default function Header() {
  const [me, setMe] = useState<any>(null);
  const [providerInfo, setProviderInfo] = useState<any>({
    model: "gemini-2.5-flash",
    name: "google_gemini",
    status: "healthy"
  });

  useEffect(() => {
    // Attempt fetching profile or login with default admin credentials if not authenticated
    async function initUser() {
      try {
        const user = await api.auth.getMe();
        setMe(user);
      } catch {
        try {
          const authData = await api.auth.login("admin@docuflow.ai", "DocuFlow2026!");
          const user = await api.auth.getMe();
          setMe(user);
        } catch (e) {
          console.warn("Could not authenticate initial user:", e);
        }
      }

      try {
        const dash = await api.dashboard.getMetrics();
        if (dash.ai_provider) {
          setProviderInfo(dash.ai_provider);
        }
      } catch (e) {
        console.warn("Could not load provider info:", e);
      }
    }
    initUser();
  }, []);

  return (
    <header className="h-16 bg-slate-900/80 backdrop-blur-md border-b border-slate-800 px-8 flex items-center justify-between sticky top-0 z-30">
      {/* Left: Organization context */}
      <div className="flex items-center gap-3">
        <div className="h-8 w-8 rounded bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
          <Building2 className="h-4 w-4" />
        </div>
        <div>
          <div className="text-sm font-semibold text-white">
            {me?.current_organization?.name || "Acme Real Estate Holdings"}
          </div>
          <div className="text-[11px] text-slate-400 capitalize">
            Role: <span className="text-emerald-400 font-medium">{me?.current_organization?.role || "Owner"}</span>
          </div>
        </div>
      </div>

      {/* Right: AI Provider Pill & User */}
      <div className="flex items-center gap-4">
        {/* Gemini Provider Pill */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/90 border border-slate-700/80 text-xs text-slate-300 shadow-sm">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="font-semibold text-slate-200">Gemini</span>
          <span className="text-slate-400 font-mono text-[11px]">{providerInfo.model}</span>
        </div>

        {/* Workspace Quick CTA */}
        <Link
          href="/workspace"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold text-xs transition-colors shadow-sm shadow-emerald-500/20"
        >
          <Sparkles className="h-3.5 w-3.5 fill-current" />
          <span>Run Agent</span>
        </Link>

        {/* User Avatar */}
        <div className="flex items-center gap-2.5 pl-3 border-l border-slate-800">
          <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-slate-700 to-slate-600 border border-slate-600 flex items-center justify-center text-white text-xs font-bold">
            {me?.user?.full_name?.charAt(0) || "A"}
          </div>
          <div className="hidden md:block text-left">
            <div className="text-xs font-medium text-white">{me?.user?.full_name || "DocuFlow Admin"}</div>
            <div className="text-[10px] text-slate-400">{me?.user?.email || "admin@docuflow.ai"}</div>
          </div>
        </div>
      </div>
    </header>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Bot,
  Users,
  FileText,
  Sparkles,
  CheckSquare,
  Workflow,
  ScrollText,
  Settings,
  ShieldCheck,
  Zap
} from "lucide-react";

const NAV_ITEMS = [
  { name: "Overview", href: "/", icon: LayoutDashboard },
  { name: "Agent Workspace", href: "/workspace", icon: Bot, badge: "AI" },
  { name: "CRM Leads", href: "/crm", icon: Users },
  { name: "Documents", href: "/documents", icon: FileText },
  { name: "Approvals Center", href: "/approvals", icon: CheckSquare, highlight: true },
  { name: "Skills Registry", href: "/skills", icon: Sparkles },
  { name: "Automations", href: "/automations", icon: Workflow },
  { name: "Audit Trail", href: "/audit", icon: ScrollText },
  { name: "Settings", href: "/settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between h-screen sticky top-0">
      <div>
        {/* Brand */}
        <div className="h-16 flex items-center px-6 border-b border-slate-800 gap-3">
          <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center text-slate-950 font-bold shadow-lg shadow-emerald-500/20">
            <Zap className="h-5 w-5 fill-current" />
          </div>
          <div>
            <div className="font-bold text-white tracking-wide flex items-center gap-1.5">
              DocuFlow <span className="text-xs px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">OS</span>
            </div>
            <div className="text-[10px] text-slate-400 uppercase tracking-wider">AI Agent Platform</div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="p-3 space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    : "text-slate-400 hover:text-white hover:bg-slate-800/60"
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`h-4 w-4 ${isActive ? "text-emerald-400" : "text-slate-400"}`} />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-400 text-slate-950">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Infrastructure Disclosure Footer */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/60">
        <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
          <ShieldCheck className="h-4 w-4 text-emerald-400" />
          <span className="font-semibold text-slate-300">Google Gemini API</span>
        </div>
        <p className="text-[11px] text-slate-500 leading-relaxed">
          Inference running via official <span className="text-slate-300">google-genai</span> Python SDK (Server-Side).
        </p>
      </div>
    </aside>
  );
}

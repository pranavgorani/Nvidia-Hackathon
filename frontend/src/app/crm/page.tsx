"use client";

import { useEffect, useState } from "react";
import {
  Users,
  Search,
  Plus,
  Phone,
  Mail,
  MapPin,
  DollarSign,
  Calendar,
  CheckCircle,
  Clock,
  FileText,
  Filter,
  X
} from "lucide-react";
import { api } from "@/lib/api";

const STATUSES = ["all", "new", "contacted", "qualified", "site_visit_scheduled", "negotiation", "won", "lost"];

export default function CRMPage() {
  const [leads, setLeads] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [search, setSearch] = useState("");
  const [selectedLead, setSelectedLead] = useState<any>(null);
  const [leadDetails, setLeadDetails] = useState<any>(null);
  const [newNote, setNewNote] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    contact_name: "",
    email: "",
    phone: "",
    preferred_location: "",
    budget_range: "",
    property_type: "Apartment",
    property_requirements: ""
  });

  async function loadLeads() {
    try {
      setLoading(true);
      const res = await api.crm.getLeads(selectedStatus === "all" ? undefined : selectedStatus, search || undefined);
      setLeads(res || []);
    } catch (e) {
      console.warn("Failed to load leads:", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadLeads();
  }, [selectedStatus]);

  async function openLeadDetails(lead: any) {
    setSelectedLead(lead);
    try {
      const details = await api.crm.getLead(lead.id);
      setLeadDetails(details);
    } catch (e) {
      console.warn("Could not load lead details:", e);
    }
  }

  async function handleAddNote() {
    if (!selectedLead || !newNote.trim()) return;
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/crm/leads/${selectedLead.id}/notes`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${localStorage.getItem("docuflow_token")}`,
          "X-Organization-Id": localStorage.getItem("docuflow_org_id") || ""
        },
        body: JSON.stringify({ content: newNote })
      });
      setNewNote("");
      const details = await api.crm.getLead(selectedLead.id);
      setLeadDetails(details);
    } catch (e) {
      alert("Failed to add note");
    }
  }

  async function handleCreateLead(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api.crm.createLead(createForm);
      setIsCreateOpen(false);
      setCreateForm({
        contact_name: "",
        email: "",
        phone: "",
        preferred_location: "",
        budget_range: "",
        property_type: "Apartment",
        property_requirements: ""
      });
      loadLeads();
    } catch (err: any) {
      alert(`Error creating lead: ${err.message}`);
    }
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Users className="h-6 w-6 text-emerald-400" />
            <span>Real Estate CRM</span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Organized lead pipeline, verified contact matching, and interaction timeline.
          </p>
        </div>

        <button
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold text-xs transition-all shadow-md shadow-emerald-500/20"
        >
          <Plus className="h-4 w-4" />
          <span>New Lead</span>
        </button>
      </div>

      {/* Filters & Search */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-slate-900/60 border border-slate-800">
        {/* Pipeline Tabs */}
        <div className="flex items-center gap-1 overflow-x-auto w-full md:w-auto pb-2 md:pb-0">
          {STATUSES.map((st) => (
            <button
              key={st}
              onClick={() => setSelectedStatus(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors whitespace-nowrap ${
                selectedStatus === st
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              }`}
            >
              {st.replace(/_/g, " ")}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative w-full md:w-64">
          <Search className="h-4 w-4 absolute left-3 top-2.5 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && loadLeads()}
            placeholder="Search name, email, location..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
          />
        </div>
      </div>

      {/* Leads Grid / Table */}
      {loading ? (
        <div className="text-center py-12 text-slate-400 text-xs">Loading CRM leads...</div>
      ) : leads.length === 0 ? (
        <div className="text-center py-16 rounded-2xl bg-slate-900/40 border border-slate-800 text-slate-500 text-xs">
          No leads found matching your criteria. Create a lead or run the Property Intake Agent to ingest inquiries.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {leads.map((lead) => (
            <div
              key={lead.id}
              onClick={() => openLeadDetails(lead)}
              className="p-5 rounded-xl bg-slate-900/70 hover:bg-slate-850/80 border border-slate-800 transition-all cursor-pointer space-y-3 shadow-md"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-bold text-sm text-white">{lead.contact_name}</h3>
                  <span className="text-[10px] text-slate-400">{lead.source || "Document Intake"}</span>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase">
                  {lead.status?.replace(/_/g, " ")}
                </span>
              </div>

              <div className="space-y-1.5 text-xs text-slate-300">
                {lead.preferred_location && (
                  <div className="flex items-center gap-1.5 text-slate-400">
                    <MapPin className="h-3.5 w-3.5 text-slate-500" />
                    <span>{lead.preferred_location}</span>
                  </div>
                )}
                {lead.budget_range && (
                  <div className="flex items-center gap-1.5 text-slate-400">
                    <DollarSign className="h-3.5 w-3.5 text-slate-500" />
                    <span>{lead.budget_range}</span>
                  </div>
                )}
                {lead.property_type && (
                  <div className="text-[11px] text-slate-400">
                    Type: <span className="text-slate-200">{lead.property_type}</span>
                    {lead.bedrooms && ` • ${lead.bedrooms} BHK`}
                  </div>
                )}
              </div>

              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500">
                <span>Priority: <strong className="text-slate-300 capitalize">{lead.priority}</strong></span>
                <span>{new Date(lead.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Lead Detail Modal */}
      {selectedLead && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto p-6 space-y-6 shadow-2xl">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-lg font-bold text-white">{selectedLead.contact_name}</h2>
                <div className="text-xs text-slate-400 flex items-center gap-3 mt-1">
                  {selectedLead.email && <span>{selectedLead.email}</span>}
                  {selectedLead.phone && <span>{selectedLead.phone}</span>}
                </div>
              </div>
              <button
                onClick={() => setSelectedLead(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs bg-slate-950/60 p-4 rounded-xl border border-slate-800">
              <div><span className="text-slate-400">Status:</span> <strong className="text-emerald-400 capitalize">{selectedLead.status?.replace(/_/g, " ")}</strong></div>
              <div><span className="text-slate-400">Priority:</span> <strong className="text-white capitalize">{selectedLead.priority}</strong></div>
              <div><span className="text-slate-400">Location:</span> <strong className="text-white">{selectedLead.preferred_location || "N/A"}</strong></div>
              <div><span className="text-slate-400">Budget:</span> <strong className="text-white">{selectedLead.budget_range || "N/A"}</strong></div>
              <div className="col-span-2 pt-1"><span className="text-slate-400">Requirements:</span> <p className="text-slate-300 mt-0.5">{selectedLead.property_requirements || "None specified"}</p></div>
            </div>

            {/* Notes Section */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">Internal Notes</h3>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newNote}
                  onChange={(e) => setNewNote(e.target.value)}
                  placeholder="Add a new note..."
                  className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                />
                <button
                  onClick={handleAddNote}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-medium rounded-lg text-slate-200"
                >
                  Post Note
                </button>
              </div>
              <div className="space-y-2 max-h-36 overflow-y-auto">
                {(leadDetails?.notes || []).map((n: any) => (
                  <div key={n.id} className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 text-xs text-slate-300">
                    <p>{n.content}</p>
                    <span className="text-[10px] text-slate-500 mt-1 block">{new Date(n.created_at).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create Lead Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <form onSubmit={handleCreateLead} className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-white">Create New CRM Lead</h2>
              <button type="button" onClick={() => setIsCreateOpen(false)} className="text-slate-400 hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Contact Name *</label>
                <input
                  type="text"
                  required
                  value={createForm.contact_name}
                  onChange={(e) => setCreateForm({ ...createForm, contact_name: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1">Email</label>
                  <input
                    type="email"
                    value={createForm.email}
                    onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Phone</label>
                  <input
                    type="text"
                    value={createForm.phone}
                    onChange={(e) => setCreateForm({ ...createForm, phone: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1">Preferred Location</label>
                  <input
                    type="text"
                    value={createForm.preferred_location}
                    onChange={(e) => setCreateForm({ ...createForm, preferred_location: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Budget Range</label>
                  <input
                    type="text"
                    placeholder="e.g. $2M - $2.5M"
                    value={createForm.budget_range}
                    onChange={(e) => setCreateForm({ ...createForm, budget_range: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Requirements</label>
                <textarea
                  rows={2}
                  value={createForm.property_requirements}
                  onChange={(e) => setCreateForm({ ...createForm, property_requirements: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500 resize-none"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setIsCreateOpen(false)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 text-xs text-slate-300 hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-1.5 rounded-lg bg-emerald-500 text-slate-950 text-xs font-semibold hover:bg-emerald-600"
              >
                Save Lead
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

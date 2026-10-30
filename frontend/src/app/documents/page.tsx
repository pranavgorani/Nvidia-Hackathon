"use client";

import { useEffect, useState } from "react";
import {
  FileText,
  Upload,
  CheckCircle,
  Clock,
  AlertTriangle,
  Sparkles,
  Edit2,
  Save,
  X,
  RefreshCw,
  FileSearch,
  ExternalLink
} from "lucide-react";
import { api } from "@/lib/api";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<any>(null);
  const [extraction, setExtraction] = useState<any>(null);
  const [editFields, setEditFields] = useState<any>({});
  const [savingReview, setSavingReview] = useState(false);
  const [processingId, setProcessingId] = useState<string | null>(null);

  async function loadDocs() {
    try {
      setLoading(true);
      const res = await api.documents.list();
      setDocuments(res || []);
    } catch (e) {
      console.warn("Failed to load documents:", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDocs();
  }, []);

  async function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setUploading(true);
      const newDoc = await api.documents.upload(file);
      await loadDocs();
      // Select the newly uploaded doc
      openDocDetails(newDoc);
    } catch (err: any) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
  }

  async function openDocDetails(doc: any) {
    setSelectedDoc(doc);
    setExtraction(null);
    setEditFields({});

    try {
      const fullDoc = await api.documents.get(doc.id);
      setSelectedDoc(fullDoc.document);
      if (fullDoc.extraction) {
        setExtraction(fullDoc.extraction);
        setEditFields({
          customer_name: fullDoc.extraction.customer_name || "",
          email: fullDoc.extraction.email || "",
          phone: fullDoc.extraction.phone || "",
          preferred_location: fullDoc.extraction.preferred_location || "",
          budget: fullDoc.extraction.budget || "",
          property_type: fullDoc.extraction.property_type || "",
          bedrooms: fullDoc.extraction.bedrooms || "",
          requirements: fullDoc.extraction.requirements || "",
        });
      }
    } catch (e) {
      console.warn("Could not load extraction details:", e);
    }
  }

  async function handleTriggerExtraction(docId: string) {
    try {
      setProcessingId(docId);
      const ext = await api.documents.process(docId);
      setExtraction(ext);
      setEditFields({
        customer_name: ext.customer_name || "",
        email: ext.email || "",
        phone: ext.phone || "",
        preferred_location: ext.preferred_location || "",
        budget: ext.budget || "",
        property_type: ext.property_type || "",
        bedrooms: ext.bedrooms || "",
        requirements: ext.requirements || "",
      });
      loadDocs();
    } catch (err: any) {
      alert(`Extraction failed: ${err.message}`);
    } finally {
      setProcessingId(null);
    }
  }

  async function handleSaveReview() {
    if (!extraction) return;
    try {
      setSavingReview(true);
      const updated = await api.documents.reviewExtraction(
        extraction.id,
        editFields,
        "Human review corrections in Documents Center"
      );
      setExtraction(updated);
      alert("Extraction review saved with traceable revision.");
    } catch (err: any) {
      alert(`Save review failed: ${err.message}`);
    } finally {
      setSavingReview(false);
    }
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <FileText className="h-6 w-6 text-emerald-400" />
            <span>Document Intelligence Pipeline</span>
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            PDF/Image text extraction, Google Gemini field intelligence, evidence snippets, and human review revisions.
          </p>
        </div>

        {/* Upload Button */}
        <label className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold text-xs cursor-pointer transition-all shadow-md shadow-emerald-500/20">
          <Upload className="h-4 w-4" />
          <span>{uploading ? "Uploading..." : "Upload Inquiry Document"}</span>
          <input
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            disabled={uploading}
            onChange={handleFileUpload}
            className="hidden"
          />
        </label>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Document List (Left 1 Col) */}
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
            <div className="text-xs font-bold text-white mb-3">All Ingested Documents</div>

            {loading ? (
              <div className="text-xs text-slate-500 py-6 text-center">Loading documents...</div>
            ) : documents.length === 0 ? (
              <div className="text-xs text-slate-500 py-8 text-center border border-dashed border-slate-800 rounded-lg">
                No documents uploaded yet. Upload a PDF or image to begin extraction.
              </div>
            ) : (
              <div className="space-y-2">
                {documents.map((d) => {
                  const isSelected = selectedDoc?.id === d.id;
                  return (
                    <div
                      key={d.id}
                      onClick={() => openDocDetails(d)}
                      className={`p-3 rounded-lg border text-xs cursor-pointer transition-all space-y-1.5 ${
                        isSelected
                          ? "bg-slate-800 border-emerald-500/40 text-white"
                          : "bg-slate-950/60 border-slate-800/80 text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <span className="font-semibold truncate max-w-[170px]">{d.original_name}</span>
                        <span
                          className={`text-[9px] px-1.5 py-0.5 rounded font-semibold uppercase ${
                            d.processing_status === "completed"
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : d.processing_status === "review_required"
                              ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                              : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                          }`}
                        >
                          {d.processing_status?.replace(/_/g, " ")}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-500 flex justify-between">
                        <span>{(d.file_size / 1024).toFixed(1)} KB</span>
                        <span>{new Date(d.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right 2 Cols: Side-by-Side Review & Evidence */}
        <div className="lg:col-span-2 space-y-6">
          {!selectedDoc ? (
            <div className="text-center py-24 rounded-2xl bg-slate-900/30 border border-slate-800 text-slate-500 text-xs">
              Select a document from the left list or upload a new file to review extracted intelligence and evidence.
            </div>
          ) : (
            <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-6">
              {/* Document Header */}
              <div className="flex items-start justify-between pb-4 border-b border-slate-800">
                <div>
                  <h2 className="text-base font-bold text-white">{selectedDoc.original_name}</h2>
                  <div className="text-xs text-slate-400 flex items-center gap-3 mt-1">
                    <span>MIME: {selectedDoc.mime_type}</span>
                    <span>Status: <strong className="text-emerald-400 capitalize">{selectedDoc.processing_status}</strong></span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleTriggerExtraction(selectedDoc.id)}
                    disabled={processingId === selectedDoc.id}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 flex items-center gap-1.5"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 ${processingId === selectedDoc.id ? "animate-spin" : ""}`} />
                    <span>Re-Extract</span>
                  </button>
                </div>
              </div>

              {/* Extraction Content */}
              {!extraction ? (
                <div className="text-center py-12 text-slate-400 text-xs space-y-3">
                  <p>Document text extracted. Click below to run AI field extraction.</p>
                  <button
                    onClick={() => handleTriggerExtraction(selectedDoc.id)}
                    className="px-4 py-2 rounded-xl bg-emerald-500 text-slate-950 font-semibold text-xs inline-flex items-center gap-2"
                  >
                    <Sparkles className="h-4 w-4" />
                    <span>Run Gemini Field Extraction</span>
                  </button>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Extracted Fields Form */}
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white uppercase tracking-wider">
                        Extracted Property Inquiry Intelligence
                      </span>
                      <span className="text-xs text-slate-400">
                        Review Status: <strong className="text-emerald-400 capitalize">{extraction.review_status}</strong>
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-4 text-xs">
                      <div>
                        <label className="text-slate-400 block mb-1">Customer Name</label>
                        <input
                          type="text"
                          value={editFields.customer_name || ""}
                          onChange={(e) => setEditFields({ ...editFields, customer_name: e.target.value })}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                        />
                        {extraction.field_metadata_json?.customer_name?.snippet && (
                          <div className="text-[10px] text-emerald-400/80 mt-1 italic">
                            Evidence: "{extraction.field_metadata_json.customer_name.snippet}"
                          </div>
                        )}
                      </div>

                      <div>
                        <label className="text-slate-400 block mb-1">Email</label>
                        <input
                          type="email"
                          value={editFields.email || ""}
                          onChange={(e) => setEditFields({ ...editFields, email: e.target.value })}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                        />
                        {extraction.field_metadata_json?.email?.snippet && (
                          <div className="text-[10px] text-emerald-400/80 mt-1 italic">
                            Evidence: "{extraction.field_metadata_json.email.snippet}"
                          </div>
                        )}
                      </div>

                      <div>
                        <label className="text-slate-400 block mb-1">Phone</label>
                        <input
                          type="text"
                          value={editFields.phone || ""}
                          onChange={(e) => setEditFields({ ...editFields, phone: e.target.value })}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                        />
                      </div>

                      <div>
                        <label className="text-slate-400 block mb-1">Preferred Location</label>
                        <input
                          type="text"
                          value={editFields.preferred_location || ""}
                          onChange={(e) => setEditFields({ ...editFields, preferred_location: e.target.value })}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                        />
                        {extraction.field_metadata_json?.preferred_location?.snippet && (
                          <div className="text-[10px] text-emerald-400/80 mt-1 italic">
                            Evidence: "{extraction.field_metadata_json.preferred_location.snippet}"
                          </div>
                        )}
                      </div>

                      <div>
                        <label className="text-slate-400 block mb-1">Budget Range</label>
                        <input
                          type="text"
                          value={editFields.budget || ""}
                          onChange={(e) => setEditFields({ ...editFields, budget: e.target.value })}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                        />
                        {extraction.field_metadata_json?.budget?.snippet && (
                          <div className="text-[10px] text-emerald-400/80 mt-1 italic">
                            Evidence: "{extraction.field_metadata_json.budget.snippet}"
                          </div>
                        )}
                      </div>

                      <div>
                        <label className="text-slate-400 block mb-1">Property Type / Bedrooms</label>
                        <div className="grid grid-cols-2 gap-2">
                          <input
                            type="text"
                            placeholder="Type"
                            value={editFields.property_type || ""}
                            onChange={(e) => setEditFields({ ...editFields, property_type: e.target.value })}
                            className="bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                          />
                          <input
                            type="number"
                            placeholder="Bedrooms"
                            value={editFields.bedrooms || ""}
                            onChange={(e) => setEditFields({ ...editFields, bedrooms: e.target.value })}
                            className="bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500"
                          />
                        </div>
                      </div>

                      <div className="col-span-2">
                        <label className="text-slate-400 block mb-1">Requirements & Amenities</label>
                        <textarea
                          rows={2}
                          value={editFields.requirements || ""}
                          onChange={(e) => setEditFields({ ...editFields, requirements: e.target.value })}
                          className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 focus:outline-none focus:border-emerald-500 resize-none"
                        />
                      </div>
                    </div>

                    <div className="flex justify-end pt-2">
                      <button
                        onClick={handleSaveReview}
                        disabled={savingReview}
                        className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold text-xs flex items-center gap-1.5 transition-all shadow-md shadow-emerald-500/20"
                      >
                        <Save className="h-3.5 w-3.5" />
                        <span>{savingReview ? "Saving Revision..." : "Save Review Correction"}</span>
                      </button>
                    </div>
                  </div>

                  {/* Raw Text Snippet */}
                  {selectedDoc.raw_text && (
                    <div className="pt-4 border-t border-slate-800">
                      <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">
                        Document Raw Text Stream
                      </span>
                      <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800/80 font-mono text-[11px] text-slate-400 whitespace-pre-wrap max-h-48 overflow-y-auto">
                        {selectedDoc.raw_text}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

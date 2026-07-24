"use client";

import React, { useState, useEffect, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { 
  BookOpen, UploadCloud, ChevronRight, FileText, Trash2, 
  RefreshCw, CheckCircle2, AlertTriangle, Layers, Database
} from "lucide-react";

interface Document {
  id: string;
  filename: string;
  file_size: number;
  page_count: number;
  processing_status: string; // uploaded, extracting, chunking, embedding, indexed, failed
  error_message: string | null;
  created_at: string;
}

export default function SourcesPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;
  const router = useRouter();

  const [project, setProject] = useState<any>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchProjectAndDocs = async () => {
    try {
      const projData = await api.getProject(projectId);
      setProject(projData);
      const docsData = await api.listDocuments(projectId);
      setDocuments(docsData);
    } catch (err: any) {
      setError(err.message || "Failed to load project details");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjectAndDocs();
  }, [projectId]);

  // Polling mechanism to check document status updates in background
  useEffect(() => {
    const activePollingDocs = documents.filter(
      (doc) => !["indexed", "failed"].includes(doc.processing_status)
    );

    if (activePollingDocs.length === 0) return;

    const interval = setInterval(async () => {
      try {
        const updatedDocs = await Promise.all(
          documents.map(async (doc) => {
            if (!["indexed", "failed"].includes(doc.processing_status)) {
              return await api.getDocumentStatus(doc.id);
            }
            return doc;
          })
        );
        setDocuments(updatedDocs);
      } catch (err) {
        console.error("Error polling document status:", err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [documents]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !e.target.files[0]) return;
    const file = e.target.files[0];
    
    if (!file.name.endsWith(".pdf")) {
      setError("Please upload PDF textbook materials only.");
      return;
    }

    setUploading(true);
    setError(null);
    try {
      const newDoc = await api.uploadDocument(projectId, file);
      setDocuments((prev) => [...prev, newDoc]);
    } catch (err: any) {
      setError(err.message || "Failed to upload document. Max size is 100MB.");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId: string) => {
    if (!confirm("Are you sure you want to delete this document? All chunks and embeddings will be wiped.")) return;

    try {
      await api.deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch (err: any) {
      setError(err.message || "Failed to delete document");
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "indexed":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
            Indexed
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20">
            <AlertTriangle className="w-3.5 h-3.5 mr-1" />
            Failed
          </span>
        );
      case "uploaded":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-neutral-800 text-neutral-400 border border-neutral-700">
            Uploaded
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
            {status.charAt(0).toUpperCase() + status.slice(1)}...
          </span>
        );
    }
  };

  if (loading) {
    return (
      <div className="flex-grow flex items-center justify-center bg-neutral-950">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-400" />
      </div>
    );
  }

  const isIndexingInProgress = documents.some(
    (doc) => !["indexed", "failed"].includes(doc.processing_status)
  );

  return (
    <div className="flex-grow flex flex-col bg-neutral-950 min-h-screen text-neutral-100 pb-16">
      {/* Header */}
      <header className="bg-neutral-900 border-b border-neutral-800 px-6 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link href="/dashboard" className="text-neutral-400 hover:text-white transition-colors">
            Dashboard
          </Link>
          <ChevronRight className="w-4 h-4 text-neutral-600" />
          <span className="text-white font-semibold">{project?.name}</span>
          <ChevronRight className="w-4 h-4 text-neutral-600" />
          <span className="text-xs px-2 py-0.5 rounded bg-neutral-800 text-neutral-400 border border-neutral-700">
            Textbooks Step
          </span>
        </div>

        <Link
          href={`/projects/${projectId}/notes`}
          className={`inline-flex items-center px-4 py-2 text-sm font-semibold rounded-lg bg-emerald-400 text-neutral-950 hover:bg-emerald-300 transition-all ${
            documents.length === 0 || isIndexingInProgress ? "opacity-50 pointer-events-none" : ""
          }`}
        >
          Study Workspace
          <ChevronRight className="w-4 h-4 ml-1" />
        </Link>
      </header>

      {/* Main Container */}
      <div className="max-w-4xl mx-auto px-4 py-10 w-full flex-grow flex flex-col">
        {/* Intro */}
        <div className="mb-8">
          <h1 className="text-3xl font-extrabold text-white">Reference Textbooks</h1>
          <p className="text-neutral-400 text-sm mt-1">
            Upload the core textbooks and reference manuals for this subject workspace. StudyForge AI will chunk, vector embed, and index them asynchronously to support grounded note generation.
          </p>
        </div>

        {error && (
          <div className="mb-6 bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-start space-x-3 text-red-400 text-sm">
            <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Uploader Box */}
          <div className="md:col-span-1">
            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 shadow-md sticky top-6">
              <h3 className="text-lg font-bold text-white mb-4">Add Textbook</h3>
              <div className="border border-dashed border-neutral-800 rounded-xl p-6 text-center bg-neutral-950/20">
                <UploadCloud className="w-10 h-10 text-neutral-600 mx-auto mb-3" />
                <p className="text-xs text-neutral-400 mb-4">Upload clean PDF textbooks up to 100MB</p>

                <label className="w-full flex items-center justify-center py-2 px-4 rounded-lg bg-neutral-900 border border-neutral-800 text-neutral-300 hover:bg-neutral-800 hover:text-white transition-all text-xs font-bold cursor-pointer disabled:opacity-50">
                  {uploading ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin mr-1.5" />
                  ) : (
                    "Upload PDF File"
                  )}
                  <input
                    type="file"
                    accept="application/pdf"
                    className="hidden"
                    disabled={uploading}
                    onChange={handleFileUpload}
                  />
                </label>
              </div>
            </div>
          </div>

          {/* Documents list */}
          <div className="md:col-span-2 space-y-4">
            <h3 className="text-lg font-bold text-white mb-2">Uploaded Materials ({documents.length})</h3>

            {documents.length === 0 ? (
              <div className="text-center py-16 bg-neutral-900/10 rounded-xl border border-dashed border-neutral-800">
                <FileText className="w-10 h-10 text-neutral-700 mx-auto mb-3" />
                <p className="text-neutral-500 text-sm">No textbook references uploaded yet.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="bg-neutral-900 border border-neutral-800 rounded-xl p-4 flex items-center justify-between hover:border-neutral-700 transition-colors shadow-sm"
                  >
                    <div className="flex items-center space-x-3 min-w-0">
                      <div className="p-2.5 rounded-lg bg-neutral-950 text-neutral-400 border border-neutral-800">
                        <FileText className="w-5 h-5" />
                      </div>
                      <div className="min-w-0">
                        <h4 className="text-sm font-bold text-white truncate" title={doc.filename}>
                          {doc.filename}
                        </h4>
                        <div className="flex items-center space-x-2 text-xs text-neutral-500 mt-1">
                          <span>{(doc.file_size / (1024 * 1024)).toFixed(1)} MB</span>
                          {doc.page_count > 0 && (
                            <>
                              <span>•</span>
                              <span>{doc.page_count} Pages</span>
                            </>
                          )}
                        </div>
                        {doc.error_message && (
                          <p className="text-xs text-red-400 mt-1 truncate max-w-md" title={doc.error_message}>
                            Error: {doc.error_message}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center space-x-4">
                      {getStatusBadge(doc.processing_status)}
                      <button
                        onClick={() => handleDelete(doc.id)}
                        className="p-1.5 rounded text-neutral-500 hover:text-red-400 hover:bg-red-500/10 transition-all"
                        title="Delete Material"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
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

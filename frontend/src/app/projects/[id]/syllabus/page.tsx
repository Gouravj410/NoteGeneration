"use client";

import React, { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { 
  BookOpen, UploadCloud, FileText, Plus, Trash2, Edit3, 
  Check, RefreshCw, AlertCircle, Save, CheckCircle2, ChevronRight
} from "lucide-react";

interface Subtopic {
  name: string;
}

interface Topic {
  name: string;
  subtopics: string[];
}

interface Module {
  module_number: number;
  title: string;
  description: string;
  topics: Topic[];
}

interface SyllabusData {
  subject: string;
  modules: Module[];
}

export default function SyllabusPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;
  const router = useRouter();

  const [project, setProject] = useState<any>(null);
  const [loadingProject, setLoadingProject] = useState(true);
  const [syllabus, setSyllabus] = useState<SyllabusData | null>(null);
  const [uploading, setUploading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);

  // Outline editing helpers
  const [editTarget, setEditTarget] = useState<{ type: "module" | "topic" | "subtopic"; modIdx: number; topIdx?: number; subIdx?: number } | null>(null);
  const [editValue, setEditValue] = useState("");

  useEffect(() => {
    const fetchProject = async () => {
      try {
        const data = await api.getProject(projectId);
        setProject(data);
      } catch (err: any) {
        setError(err.message || "Failed to load project metadata");
      } finally {
        setLoadingProject(false);
      }
    };
    fetchProject();
  }, [projectId]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const data = await api.uploadSyllabus(projectId, file);
      setSyllabus(data);
    } catch (err: any) {
      setError(err.message || "Failed to extract syllabus. Please ensure it is a valid text PDF.");
    } finally {
      setUploading(false);
    }
  };

  const handleConfirm = async () => {
    if (!syllabus) return;
    setConfirming(true);
    setError(null);
    try {
      await api.confirmSyllabus(projectId, syllabus);
      // Navigate to the central workspace (Phase 3/4/5)
      router.push(`/projects/${projectId}/sources`);
    } catch (err: any) {
      setError(err.message || "Failed to save syllabus. Try editing values and resubmitting.");
    } finally {
      setConfirming(false);
    }
  };

  // --- Tree outline editing operations ---

  const startEdit = (type: "module" | "topic" | "subtopic", currentVal: string, modIdx: number, topIdx?: number, subIdx?: number) => {
    setEditTarget({ type, modIdx, topIdx, subIdx });
    setEditValue(currentVal);
  };

  const saveEdit = () => {
    if (!syllabus || !editTarget) return;

    const updated = { ...syllabus };
    const { type, modIdx, topIdx, subIdx } = editTarget;

    if (type === "module") {
      updated.modules[modIdx].title = editValue;
    } else if (type === "topic" && topIdx !== undefined) {
      updated.modules[modIdx].topics[topIdx].name = editValue;
    } else if (type === "subtopic" && topIdx !== undefined && subIdx !== undefined) {
      updated.modules[modIdx].topics[topIdx].subtopics[subIdx] = editValue;
    }

    setSyllabus(updated);
    setEditTarget(null);
  };

  const deleteItem = (type: "module" | "topic" | "subtopic", modIdx: number, topIdx?: number, subIdx?: number) => {
    if (!syllabus) return;

    const updated = { ...syllabus };

    if (type === "module") {
      updated.modules.splice(modIdx, 1);
      // Re-index module numbers
      updated.modules = updated.modules.map((m, i) => ({ ...m, module_number: i + 1 }));
    } else if (type === "topic" && topIdx !== undefined) {
      updated.modules[modIdx].topics.splice(topIdx, 1);
    } else if (type === "subtopic" && topIdx !== undefined && subIdx !== undefined) {
      updated.modules[modIdx].topics[topIdx].subtopics.splice(subIdx, 1);
    }

    setSyllabus(updated);
  };

  const addItem = (type: "module" | "topic" | "subtopic", modIdx: number, topIdx?: number) => {
    if (!syllabus) return;

    const updated = { ...syllabus };

    if (type === "module") {
      updated.modules.push({
        module_number: updated.modules.length + 1,
        title: "New Module Title",
        description: "",
        topics: [],
      });
    } else if (type === "topic") {
      updated.modules[modIdx].topics.push({
        name: "New Topic Name",
        subtopics: [],
      });
    } else if (type === "subtopic" && topIdx !== undefined) {
      updated.modules[modIdx].topics[topIdx].subtopics.push("New Subtopic");
    }

    setSyllabus(updated);
  };

  if (loadingProject) {
    return (
      <div className="flex-grow flex items-center justify-center bg-neutral-950">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-400" />
      </div>
    );
  }

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
          <span className="text-xs px-2 py-0.5 rounded bg-neutral-800 text-neutral-400 border border-neutral-700">
            Syllabus Step
          </span>
        </div>
      </header>

      {/* Workspace */}
      <div className="max-w-4xl mx-auto px-4 py-10 w-full">
        {/* Step Intro */}
        <div className="mb-8">
          <h1 className="text-3xl font-extrabold text-white">Syllabus Extractor</h1>
          <p className="text-neutral-400 text-sm mt-1">
            Before importing textbook references, define the active syllabus structure. Upload your PDF syllabus below to let the AI extract your modules and topics automatically.
          </p>
        </div>

        {error && (
          <div className="mb-6 bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-start space-x-3 text-red-400 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Uploader View */}
        {!syllabus && (
          <div className="bg-neutral-900 rounded-xl border border-neutral-800 p-8 text-center max-w-xl mx-auto shadow-md">
            <div className="border-2 border-dashed border-neutral-800 rounded-xl p-10 flex flex-col items-center justify-center hover:border-neutral-700 transition-all bg-neutral-950/20">
              <UploadCloud className="w-12 h-12 text-neutral-500 mb-4" />
              <p className="text-sm text-neutral-300 font-semibold mb-1">
                {file ? file.name : "Select syllabus PDF file"}
              </p>
              <p className="text-xs text-neutral-500 mb-6">PDF format up to 20MB</p>

              <label className="inline-flex items-center px-4 py-2 rounded-lg bg-neutral-900 border border-neutral-800 text-neutral-300 hover:bg-neutral-800 hover:text-white transition-all text-sm font-semibold cursor-pointer mb-4">
                Choose File
                <input type="file" accept="application/pdf" className="hidden" onChange={handleFileChange} />
              </label>

              {file && (
                <button
                  onClick={handleUpload}
                  disabled={uploading}
                  className="w-full flex items-center justify-center py-2.5 rounded-lg bg-emerald-400 hover:bg-emerald-300 text-neutral-950 font-bold text-sm shadow-sm transition-all disabled:opacity-50"
                >
                  {uploading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin mr-2" />
                      Analyzing Structure...
                    </>
                  ) : (
                    "Upload & Process Syllabus"
                  )}
                </button>
              )}
            </div>
          </div>
        )}

        {/* Outline Editor Tree View */}
        {syllabus && (
          <div className="space-y-6">
            <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 shadow-md">
              <div className="flex items-center justify-between mb-6 pb-4 border-b border-neutral-800">
                <div>
                  <span className="text-xs uppercase text-neutral-500 font-semibold tracking-wider">Subject Title</span>
                  <h2 className="text-2xl font-bold text-white mt-0.5">{syllabus.subject}</h2>
                </div>
                <button
                  onClick={() => addItem("module", 0)}
                  className="inline-flex items-center px-3 py-1.5 rounded-lg bg-neutral-800 border border-neutral-700 text-neutral-300 hover:bg-neutral-700 hover:text-white transition-all text-xs font-semibold"
                >
                  <Plus className="w-3.5 h-3.5 mr-1" />
                  Add Module
                </button>
              </div>

              {/* Module Tree nodes */}
              <div className="space-y-6">
                {syllabus.modules.map((mod, modIdx) => (
                  <div key={modIdx} className="border border-neutral-800 rounded-xl p-4 bg-neutral-950/20">
                    <div className="flex items-center justify-between group mb-4">
                      {editTarget?.type === "module" && editTarget.modIdx === modIdx ? (
                        <div className="flex items-center space-x-2 w-full max-w-md">
                          <input
                            type="text"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            className="bg-neutral-950 border border-neutral-800 rounded px-2.5 py-1 text-sm text-white focus:outline-none focus:border-emerald-500 w-full"
                          />
                          <button onClick={saveEdit} className="p-1 text-emerald-400 bg-emerald-500/10 rounded">
                            <Check className="w-4 h-4" />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center space-x-3">
                          <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            Module {mod.module_number}
                          </span>
                          <h3 className="text-lg font-bold text-white">{mod.title}</h3>
                          <button
                            onClick={() => startEdit("module", mod.title, modIdx)}
                            className="p-1 text-neutral-500 hover:text-white transition-all opacity-0 group-hover:opacity-100"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}

                      <div className="flex items-center space-x-2 opacity-0 group-hover:opacity-100 transition-all">
                        <button
                          onClick={() => addItem("topic", modIdx)}
                          className="p-1.5 text-neutral-400 hover:text-white bg-neutral-900 border border-neutral-800 rounded-lg"
                          title="Add Topic"
                        >
                          <Plus className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => deleteItem("module", modIdx)}
                          className="p-1.5 text-neutral-500 hover:text-red-400 bg-neutral-900 border border-neutral-800 rounded-lg"
                          title="Delete Module"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Topics Tree nodes */}
                    <div className="space-y-4 ml-6 border-l border-neutral-800/80 pl-6">
                      {mod.topics.map((top, topIdx) => (
                        <div key={topIdx} className="group relative">
                          <div className="flex items-center justify-between mb-2">
                            {editTarget?.type === "topic" && editTarget.modIdx === modIdx && editTarget.topIdx === topIdx ? (
                              <div className="flex items-center space-x-2 w-full max-w-sm">
                                <input
                                  type="text"
                                  value={editValue}
                                  onChange={(e) => setEditValue(e.target.value)}
                                  className="bg-neutral-950 border border-neutral-800 rounded px-2.5 py-1 text-xs text-white focus:outline-none w-full"
                                />
                                <button onClick={saveEdit} className="p-1 text-emerald-400 bg-emerald-500/10 rounded">
                                  <Check className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            ) : (
                              <div className="flex items-center space-x-2">
                                <h4 className="text-sm font-semibold text-neutral-200">{top.name}</h4>
                                <button
                                  onClick={() => startEdit("topic", top.name, modIdx, topIdx)}
                                  className="p-1 text-neutral-600 hover:text-white transition-all opacity-0 group-hover:opacity-100"
                                >
                                  <Edit3 className="w-3 h-3" />
                                </button>
                              </div>
                            )}

                            <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-all">
                              <button
                                onClick={() => addItem("subtopic", modIdx, topIdx)}
                                className="p-1 text-neutral-400 hover:text-white rounded"
                                title="Add Subtopic"
                              >
                                <Plus className="w-3 h-3" />
                              </button>
                              <button
                                onClick={() => deleteItem("topic", modIdx, topIdx)}
                                className="p-1 text-neutral-600 hover:text-red-400 rounded"
                                title="Delete Topic"
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            </div>
                          </div>

                          {/* Subtopics Nodes */}
                          <div className="flex flex-wrap gap-2 ml-4">
                            {top.subtopics.map((sub, subIdx) => (
                              <div
                                key={subIdx}
                                className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded bg-neutral-900 border border-neutral-800 hover:border-neutral-700 text-xs text-neutral-400"
                              >
                                {editTarget?.type === "subtopic" &&
                                editTarget.modIdx === modIdx &&
                                editTarget.topIdx === topIdx &&
                                editTarget.subIdx === subIdx ? (
                                  <div className="flex items-center space-x-1">
                                    <input
                                      type="text"
                                      value={editValue}
                                      onChange={(e) => setEditValue(e.target.value)}
                                      className="bg-neutral-950 border border-neutral-800 rounded px-1 text-xs text-white focus:outline-none w-28"
                                      autoFocus
                                    />
                                    <button onClick={saveEdit} className="text-emerald-400">
                                      <Check className="w-3 h-3" />
                                    </button>
                                  </div>
                                ) : (
                                  <>
                                    <span>{sub}</span>
                                    <button
                                      onClick={() => startEdit("subtopic", sub, modIdx, topIdx, subIdx)}
                                      className="text-neutral-600 hover:text-white"
                                    >
                                      <Edit3 className="w-2.5 h-2.5" />
                                    </button>
                                    <button
                                      onClick={() => deleteItem("subtopic", modIdx, topIdx, subIdx)}
                                      className="text-neutral-600 hover:text-red-400"
                                    >
                                      <Trash2 className="w-2.5 h-2.5" />
                                    </button>
                                  </>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Confirm CTA */}
            <div className="flex justify-end mt-8">
              <button
                onClick={handleConfirm}
                disabled={confirming}
                className="inline-flex items-center px-6 py-3 rounded-xl bg-emerald-400 hover:bg-emerald-300 text-neutral-950 font-bold transition-all shadow-md"
              >
                {confirming ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin mr-2" />
                    Confirming Syllabus Outline...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-5 h-5 mr-2" />
                    Confirm Syllabus Outline
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

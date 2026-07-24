"use client";

import React, { useState, useEffect, use } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { 
  ChevronRight, RefreshCw, BookOpen, CheckCircle2, Circle, Clock,
  Sparkles, Save, Eye, Edit3, MessageSquare, Bookmark, Compass,
  ChevronDown, Send, FileText, LayoutList, ChevronLeft, ArrowRight, User
} from "lucide-react";

interface Subtopic {
  id: string;
  name: string;
  status: string;
}

interface Topic {
  id: string;
  name: string;
  status: string; // not_started, in_progress, completed
  subtopics: Subtopic[];
}

interface Module {
  id: string;
  module_number: number;
  title: string;
  topics: Topic[];
}

interface Citation {
  id: string;
  document_filename: string;
  pdf_page_start: number;
  pdf_page_end: number;
  citation_label: string;
}

interface NoteVersion {
  id: string;
  content: string;
  version_number: number;
  created_by_type: "ai" | "user";
  citations: Citation[];
}

interface NoteData {
  id: string;
  canonical_content: string;
  mode: string;
  coverage_score: number;
  source_grounding_status: string;
  active_version: NoteVersion | null;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: any[];
}

export default function NotesWorkspace({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;

  const [project, setProject] = useState<any>(null);
  const [syllabus, setSyllabus] = useState<any>(null);
  const [loadingWorkspace, setLoadingWorkspace] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Active state
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);
  const [note, setNote] = useState<NoteData | null>(null);
  const [loadingNote, setLoadingNote] = useState(false);
  const [noteError, setNoteError] = useState<string | null>(null);

  // Editor states
  const [editMode, setEditMode] = useState<"preview" | "edit">("preview");
  const [editorContent, setEditorContent] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const [generatingNote, setGeneratingNote] = useState(false);
  const [generationStep, setGenerationStep] = useState("");

  // Right sidebar states
  const [activeTab, setActiveTab] = useState<"citations" | "tutor">("citations");
  const [tutorQuery, setTutorQuery] = useState("");
  const [tutorMessages, setTutorMessages] = useState<ChatMessage[]>([]);
  const [askingTutor, setAskingTutor] = useState(false);

  // Sidebar visibility on mobile
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const loadWorkspace = async () => {
    try {
      const proj = await api.getProject(projectId);
      setProject(proj);
      const syl = await api.getActiveSyllabus(projectId);
      setSyllabus(syl);
    } catch (err: any) {
      setError(err.message || "Failed to load project outline.");
    } finally {
      setLoadingWorkspace(false);
    }
  };

  useEffect(() => {
    loadWorkspace();
  }, [projectId]);

  const handleExport = async (format: "pdf" | "docx") => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/notes/${projectId}/export/${format}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`
          }
        }
      );
      if (!response.ok) {
        alert("Export failed: Please ensure you have generated notes for at least one topic.");
        return;
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${project?.name.toLowerCase().replace(/\s+/g, "_")}_notes.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      alert("Error exporting study guide: " + err);
    }
  };

  const selectTopic = async (topic: Topic) => {
    setSelectedTopic(topic);
    setLoadingNote(true);
    setNoteError(null);
    setNote(null);
    setEditMode("preview");
    setTutorMessages([]); // Reset chat context for new topic

    try {
      const data = await api.getNote(projectId, topic.id);
      setNote(data);
      setEditorContent(data.canonical_content);
    } catch (err: any) {
      // 404 is expected if notes haven't been generated yet
      if (err.status === 404) {
        setNote(null);
      } else {
        setNoteError(err.message || "Failed to fetch topic study notes.");
      }
    } finally {
      setLoadingNote(false);
    }
  };

  const handleGenerateNote = async () => {
    if (!selectedTopic) return;
    setGeneratingNote(true);
    setNoteError(null);
    
    // Simulate generation steps for high-fidelity user feedback
    const steps = [
      "Consulting research planner...",
      "Executing vector & FTS hybrid searches...",
      "Filtering textbook chunk candidates...",
      "Analyzing layout citations...",
      "Writing grounded study notes..."
    ];

    let stepIdx = 0;
    setGenerationStep(steps[0]);
    const stepInterval = setInterval(() => {
      if (stepIdx < steps.length - 1) {
        stepIdx++;
        setGenerationStep(steps[stepIdx]);
      }
    }, 1500);

    try {
      const data = await api.generateNote(projectId, selectedTopic.id);
      clearInterval(stepInterval);
      setNote(data);
      setEditorContent(data.canonical_content);
      
      // Reload syllabus outline to update completed checklist status
      const updatedSyl = await api.getActiveSyllabus(projectId);
      setSyllabus(updatedSyl);
    } catch (err: any) {
      clearInterval(stepInterval);
      setNoteError(err.message || "Notes generation failed.");
    } finally {
      setGeneratingNote(false);
      setGenerationStep("");
    }
  };

  const handleSaveNote = async () => {
    if (!selectedTopic || !note) return;
    setSavingNote(true);
    try {
      const updated = await api.saveNote(projectId, selectedTopic.id, editorContent);
      setNote(updated);
      setEditMode("preview");
    } catch (err: any) {
      setNoteError(err.message || "Failed to save edits");
    } finally {
      setSavingNote(false);
    }
  };

  const handleSendTutorMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tutorQuery.trim() || askingTutor) return;

    const userMsg: ChatMessage = { role: "user", content: tutorQuery };
    setTutorMessages((prev) => [...prev, userMsg]);
    const messageToSend = tutorQuery;
    setTutorQuery("");
    setAskingTutor(true);

    try {
      const prevHistory = tutorMessages.map((m) => ({ role: m.role, content: m.content }));
      const response = await api.askTutor(projectId, messageToSend, prevHistory);
      
      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: response.response,
        sources: response.sources
      };
      setTutorMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      setTutorMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, I had an error looking up that query." }
      ]);
    } finally {
      setAskingTutor(false);
    }
  };

  // Completion metrics
  const getProgressInfo = () => {
    if (!syllabus) return { total: 0, completed: 0, pct: 0 };
    let total = 0;
    let completed = 0;
    syllabus.modules.forEach((mod: any) => {
      mod.topics.forEach((t: any) => {
        total++;
        if (t.status === "completed") completed++;
      });
    });
    return {
      total,
      completed,
      pct: total > 0 ? Math.round((completed / total) * 100) : 0
    };
  };

  if (loadingWorkspace) {
    return (
      <div className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center text-neutral-100">
        <RefreshCw className="w-10 h-10 animate-spin text-emerald-400 mb-4" />
        <p className="text-neutral-400 text-sm">Opening Course Workspace...</p>
      </div>
    );
  }

  const { total, completed, pct } = getProgressInfo();

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col h-screen overflow-hidden">
      {/* Workspace Header */}
      <header className="bg-neutral-900 border-b border-neutral-800 px-6 h-14 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-3">
          <Link href="/dashboard" className="text-neutral-400 hover:text-white transition-colors text-sm">
            Dashboard
          </Link>
          <ChevronRight className="w-4 h-4 text-neutral-600" />
          <span className="font-semibold text-white text-sm truncate max-w-[200px]">{project?.name}</span>
          <span className="hidden md:inline-flex items-center px-2 py-0.5 rounded text-[11px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            {completed}/{total} Topics Done ({pct}%)
          </span>
        </div>

        <div className="flex items-center space-x-2.5">
          {completed > 0 && (
            <>
              <button
                onClick={() => handleExport("pdf")}
                className="text-emerald-400 hover:text-emerald-300 text-xs border border-emerald-500/20 bg-emerald-500/5 rounded px-2.5 py-1 transition-colors flex items-center font-bold"
              >
                Export PDF
              </button>
              <button
                onClick={() => handleExport("docx")}
                className="text-neutral-400 hover:text-white text-xs border border-neutral-800 rounded px-2.5 py-1 transition-colors flex items-center"
              >
                Export Word
              </button>
            </>
          )}
          <Link
            href={`/projects/${projectId}/sources`}
            className="text-neutral-400 hover:text-white text-xs border border-neutral-800 rounded px-2.5 py-1 transition-colors"
          >
            Manage Textbooks
          </Link>
        </div>
      </header>

      {/* Main Panel grid */}
      <div className="flex flex-row flex-grow overflow-hidden w-full">
        
        {/* Left Panel - Navigation Outline */}
        <aside className={`${sidebarOpen ? 'w-80' : 'w-0'} bg-neutral-900/50 border-r border-neutral-800 flex flex-col shrink-0 transition-all duration-300 overflow-hidden`}>
          <div className="p-4 border-b border-neutral-800">
            <h3 className="text-sm font-bold text-white flex items-center">
              <LayoutList className="w-4 h-4 text-emerald-400 mr-2" />
              Syllabus Outline
            </h3>
            {/* Progress bar */}
            <div className="mt-3">
              <div className="flex justify-between text-[11px] text-neutral-500 mb-1">
                <span>Course Progress</span>
                <span>{pct}%</span>
              </div>
              <div className="h-1.5 w-full bg-neutral-800 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-400 transition-all duration-500" style={{ width: `${pct}%` }}></div>
              </div>
            </div>
          </div>

          <div className="flex-grow overflow-y-auto p-4 space-y-4 custom-scrollbar">
            {syllabus?.modules.map((mod: any) => (
              <div key={mod.id} className="space-y-1.5">
                <h4 className="text-[11px] font-bold tracking-wider text-neutral-500 uppercase px-2">
                  Module {mod.module_number}: {mod.title}
                </h4>
                <div className="space-y-0.5">
                  {mod.topics.map((top: Topic) => (
                    <button
                      key={top.id}
                      onClick={() => selectTopic(top)}
                      className={`w-full flex items-center justify-between text-left px-2.5 py-2 rounded-lg text-xs font-semibold group transition-all ${
                        selectedTopic?.id === top.id
                          ? "bg-neutral-800 text-white"
                          : "text-neutral-400 hover:bg-neutral-900/50 hover:text-white"
                      }`}
                    >
                      <span className="truncate max-w-[200px]">{top.name}</span>
                      {top.status === "completed" ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 ml-1.5" />
                      ) : (
                        <Circle className="w-3.5 h-3.5 text-neutral-600 group-hover:text-neutral-500 shrink-0 ml-1.5" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </aside>

        {/* Center Panel - Notes Editor */}
        <main className="flex-grow flex flex-col bg-neutral-950 overflow-hidden relative">
          {/* Toggle sidebar button */}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="absolute top-1/2 left-0 transform -translate-y-1/2 bg-neutral-900 border border-neutral-800 text-neutral-500 hover:text-white p-1 rounded-r border-l-0 z-10"
          >
            {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>

          {!selectedTopic ? (
            <div className="flex-grow flex flex-col items-center justify-center p-10 text-center select-none">
              <div className="p-4 rounded-full bg-neutral-900/50 border border-neutral-800 text-neutral-600 mb-4">
                <BookOpen className="w-12 h-12" />
              </div>
              <h2 className="text-xl font-bold text-white mb-2">Select a Syllabus Topic</h2>
              <p className="text-sm text-neutral-500 max-w-sm">
                Choose any module topic from the left sidebar to generate or review textbook-grounded study notes.
              </p>
            </div>
          ) : (
            <div className="flex-grow flex flex-col overflow-hidden">
              {/* Note Header / Controls */}
              <div className="h-14 border-b border-neutral-800 px-6 flex items-center justify-between shrink-0 bg-neutral-900/10">
                <div className="min-w-0">
                  <h2 className="text-sm font-bold text-white truncate">{selectedTopic.name}</h2>
                </div>

                {note && (
                  <div className="flex items-center space-x-2">
                    {/* Preview / Edit Toggle */}
                    <div className="flex rounded-lg bg-neutral-900 p-0.5 border border-neutral-800">
                      <button
                        onClick={() => setEditMode("preview")}
                        className={`flex items-center px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${
                          editMode === "preview"
                            ? "bg-neutral-800 text-white shadow-sm"
                            : "text-neutral-400 hover:text-white"
                        }`}
                      >
                        <Eye className="w-3.5 h-3.5 mr-1" />
                        Preview
                      </button>
                      <button
                        onClick={() => setEditMode("edit")}
                        className={`flex items-center px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${
                          editMode === "edit"
                            ? "bg-neutral-800 text-white shadow-sm"
                            : "text-neutral-400 hover:text-white"
                        }`}
                      >
                        <Edit3 className="w-3.5 h-3.5 mr-1" />
                        Edit
                      </button>
                    </div>

                    {editMode === "edit" ? (
                      <button
                        onClick={handleSaveNote}
                        disabled={savingNote}
                        className="inline-flex items-center px-3 py-1.5 rounded-lg bg-emerald-400 hover:bg-emerald-300 text-neutral-950 text-xs font-bold transition-all disabled:opacity-50"
                      >
                        {savingNote ? (
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <>
                            <Save className="w-3.5 h-3.5 mr-1" />
                            Save version
                          </>
                        )}
                      </button>
                    ) : (
                      <button
                        onClick={handleGenerateNote}
                        disabled={generatingNote}
                        className="inline-flex items-center px-3 py-1.5 rounded-lg bg-neutral-900 hover:bg-neutral-800 border border-neutral-800 text-neutral-300 hover:text-white text-xs font-bold transition-all"
                      >
                        <Sparkles className="w-3.5 h-3.5 mr-1 text-emerald-400" />
                        Regenerate
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* Note Content Panel */}
              <div className="flex-grow overflow-y-auto p-6 md:p-8 custom-scrollbar">
                {loadingNote && (
                  <div className="h-full flex flex-col items-center justify-center">
                    <RefreshCw className="w-8 h-8 animate-spin text-emerald-400 mb-2" />
                    <p className="text-xs text-neutral-500">Loading topic notes...</p>
                  </div>
                )}

                {generatingNote && (
                  <div className="h-full flex flex-col items-center justify-center p-6 text-center">
                    <div className="relative mb-6">
                      <div className="w-16 h-16 rounded-full border-2 border-dashed border-emerald-400/30 animate-spin"></div>
                      <Sparkles className="w-6 h-6 text-emerald-400 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
                    </div>
                    <h3 className="text-lg font-bold text-white mb-2">Generating Textbook-Grounded Notes</h3>
                    <p className="text-xs text-emerald-400 font-mono max-w-sm">{generationStep}</p>
                  </div>
                )}

                {!loadingNote && !generatingNote && !note && (
                  <div className="h-full flex flex-col items-center justify-center text-center p-8">
                    <div className="w-12 h-12 rounded-full bg-neutral-900 border border-neutral-800 text-neutral-500 flex items-center justify-center mb-4">
                      <Sparkles className="w-6 h-6 text-emerald-400" />
                    </div>
                    <h3 className="text-base font-bold text-white mb-2">No Study Notes Generated</h3>
                    <p className="text-xs text-neutral-500 max-w-sm mb-6">
                      StudyForge AI will query your reference textbooks, expand searching terms, and draft complete syllabus-aligned study guides.
                    </p>
                    <button
                      onClick={handleGenerateNote}
                      className="inline-flex items-center px-4 py-2 rounded-lg bg-emerald-400 hover:bg-emerald-300 text-neutral-950 font-bold text-xs shadow-md transition-all"
                    >
                      <Sparkles className="w-4 h-4 mr-1.5" />
                      Generate Study Guide
                    </button>
                  </div>
                )}

                {!loadingNote && !generatingNote && note && (
                  <div className="max-w-2xl mx-auto h-full">
                    {editMode === "edit" ? (
                      <textarea
                        value={editorContent}
                        onChange={(e) => setEditorContent(e.target.value)}
                        className="w-full h-[80%] bg-transparent border-0 resize-none font-mono text-xs text-neutral-300 focus:ring-0 focus:outline-none custom-scrollbar"
                        placeholder="Write study notes in Markdown..."
                      />
                    ) : (
                      <div className="prose prose-invert prose-emerald max-w-none text-neutral-300 pb-16 text-xs leading-relaxed">
                        {/* Render simple markdown styling */}
                        {editorContent.split("\n\n").map((para, pIdx) => {
                          if (para.startsWith("# ")) {
                            return <h1 key={pIdx} className="text-xl font-bold text-white mt-6 mb-3">{para.replace("# ", "")}</h1>;
                          }
                          if (para.startsWith("## ")) {
                            return <h2 key={pIdx} className="text-base font-bold text-white mt-5 mb-2.5">{para.replace("## ", "")}</h2>;
                          }
                          if (para.startsWith("### ")) {
                            return <h3 key={pIdx} className="text-sm font-bold text-white mt-4 mb-2">{para.replace("### ", "")}</h3>;
                          }
                          
                          // Format inline Ref citations into highlighted tags
                          // E.g. [Ref_1]
                          const processedPara = para.split(/(\[Ref_\d+\])/g).map((token, tIdx) => {
                            const refMatch = token.match(/\[Ref_(\d+)\]/);
                            if (refMatch) {
                              const refNum = refMatch[1];
                              return (
                                <span
                                  key={tIdx}
                                  onClick={() => {
                                    setActiveTab("citations");
                                    // Highlight citation in sidebar if clicked
                                  }}
                                  className="mx-0.5 inline-flex items-center px-1.5 py-0.5 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 text-[10px] font-bold border border-emerald-500/20 cursor-pointer transition-all"
                                  title={`Reference ${refNum}`}
                                >
                                  {refNum}
                                </span>
                              );
                            }
                            return token;
                          });

                          return <p key={pIdx} className="mb-4">{processedPara}</p>;
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </main>

        {/* Right Sidebar Panel - Citations & AI Tutor */}
        <aside className="w-80 bg-neutral-900/50 border-l border-neutral-800 flex flex-col shrink-0 overflow-hidden">
          {/* Tabs header */}
          <div className="flex border-b border-neutral-800 shrink-0">
            <button
              onClick={() => setActiveTab("citations")}
              className={`flex-1 py-3 text-xs font-bold flex items-center justify-center border-b-2 transition-all ${
                activeTab === "citations"
                  ? "border-emerald-400 text-white"
                  : "border-transparent text-neutral-500 hover:text-neutral-300"
              }`}
            >
              <Bookmark className="w-3.5 h-3.5 mr-1.5" />
              Citations
            </button>
            <button
              onClick={() => setActiveTab("tutor")}
              className={`flex-1 py-3 text-xs font-bold flex items-center justify-center border-b-2 transition-all ${
                activeTab === "tutor"
                  ? "border-emerald-400 text-white"
                  : "border-transparent text-neutral-500 hover:text-neutral-300"
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5 mr-1.5" />
              AI Tutor
            </button>
          </div>

          <div className="flex-grow overflow-hidden flex flex-col">
            
            {/* Citations Tab */}
            {activeTab === "citations" && (
              <div className="flex-grow overflow-y-auto p-4 space-y-3 custom-scrollbar">
                {!note || !note.active_version?.citations || note.active_version.citations.length === 0 ? (
                  <div className="text-center py-16 text-neutral-600">
                    <FileText className="w-10 h-10 mx-auto mb-3 opacity-50" />
                    <p className="text-xs">No citations for this topic notes version.</p>
                  </div>
                ) : (
                  <>
                    <h4 className="text-[10px] font-bold uppercase tracking-wider text-neutral-500 px-1 mb-2">
                      Grounded Sources ({note.active_version.citations.length})
                    </h4>
                    <div className="space-y-2">
                      {note.active_version.citations.map((cit) => (
                        <div
                          key={cit.id}
                          className="bg-neutral-900 border border-neutral-800 rounded-xl p-3 hover:border-neutral-700 transition-colors shadow-sm"
                        >
                          <div className="flex items-center justify-between mb-1.5">
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 font-bold border border-emerald-500/20">
                              Ref {cit.citation_label.replace(/\D/g, "")}
                            </span>
                            <span className="text-[10px] text-neutral-500">
                              Pages: {cit.pdf_page_start}-{cit.pdf_page_end}
                            </span>
                          </div>
                          <h5 className="text-xs font-bold text-white truncate" title={cit.document_filename}>
                            {cit.document_filename}
                          </h5>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}

            {/* AI Tutor Chat Tab */}
            {activeTab === "tutor" && (
              <div className="flex-grow flex flex-col overflow-hidden h-full">
                {/* Messages list */}
                <div className="flex-grow overflow-y-auto p-4 space-y-4 custom-scrollbar">
                  {tutorMessages.length === 0 ? (
                    <div className="text-center py-16 text-neutral-600">
                      <Compass className="w-10 h-10 mx-auto mb-3 opacity-50 text-emerald-400" />
                      <h4 className="text-xs font-bold text-neutral-400 mb-1">Grounded Tutor Chat</h4>
                      <p className="text-[11px] max-w-[200px] mx-auto text-neutral-500 leading-normal">
                        Ask any academic follow-up question. The tutor answers using context only from your textbook chapters.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {tutorMessages.map((msg, idx) => (
                        <div key={idx} className="space-y-1.5">
                          <div className="flex items-center space-x-2">
                            {msg.role === "user" ? (
                              <div className="p-1 rounded bg-neutral-800 text-neutral-400 border border-neutral-700 shrink-0">
                                <User className="w-3 h-3" />
                              </div>
                            ) : (
                              <div className="p-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shrink-0">
                                <Compass className="w-3 h-3" />
                              </div>
                            )}
                            <span className="text-[10px] font-bold text-neutral-500">
                              {msg.role === "user" ? "You" : "StudyForge AI Tutor"}
                            </span>
                          </div>
                          <div className={`p-3 rounded-xl border text-xs leading-relaxed ${
                            msg.role === "user"
                              ? "bg-neutral-900 border-neutral-800 text-neutral-200"
                              : "bg-emerald-500/[0.02] border-emerald-500/10 text-neutral-300"
                          }`}>
                            <p>{msg.content}</p>

                            {/* Render cited sources from response */}
                            {msg.sources && msg.sources.length > 0 && (
                              <div className="mt-3 pt-2.5 border-t border-neutral-800 space-y-1">
                                <span className="text-[9px] font-bold text-neutral-500 uppercase tracking-wider">
                                  References Used
                                </span>
                                <div className="space-y-1">
                                  {msg.sources.map((src: any, sIdx: number) => (
                                    <div key={sIdx} className="text-[10px] text-neutral-400 flex items-center space-x-1.5 truncate">
                                      <span className="text-[9px] font-bold text-emerald-400 bg-emerald-500/10 px-1 rounded">
                                        {src.label}
                                      </span>
                                      <span className="truncate" title={src.document_filename}>
                                        {src.document_filename} (p. {src.printed_pages})
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {askingTutor && (
                    <div className="flex items-center space-x-2 text-neutral-500 text-xs py-2">
                      <RefreshCw className="w-3.5 h-3.5 animate-spin text-emerald-400" />
                      <span>Tutor is researching textbooks...</span>
                    </div>
                  )}
                </div>

                {/* Input form */}
                <form onSubmit={handleSendTutorMessage} className="p-3 border-t border-neutral-800 bg-neutral-900/20 shrink-0">
                  <div className="relative">
                    <input
                      type="text"
                      value={tutorQuery}
                      onChange={(e) => setTutorQuery(e.target.value)}
                      placeholder="Ask the grounded AI Tutor..."
                      disabled={askingTutor}
                      className="w-full bg-neutral-900 border border-neutral-800 hover:border-neutral-700 focus:border-emerald-500 focus:outline-none rounded-xl py-2 px-3.5 pr-10 text-xs text-white placeholder-neutral-500 transition-colors"
                    />
                    <button
                      type="submit"
                      disabled={!tutorQuery.trim() || askingTutor}
                      className="absolute right-1.5 top-1/2 transform -translate-y-1/2 p-1.5 text-emerald-400 hover:text-emerald-300 disabled:opacity-50 transition-colors"
                    >
                      <Send className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </form>
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

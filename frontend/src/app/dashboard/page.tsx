"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { 
  BookOpen, Plus, Folder, Trash2, Calendar, 
  ChevronRight, RefreshCw, AlertCircle, LogOut, User
} from "lucide-react";

interface Project {
  id: string;
  name: string;
  subject: string;
  course: string | null;
  semester: string | null;
  university: string | null;
  preferred_language: string;
  created_at: string;
}

export default function DashboardPage() {
  const { user, logout, loading: authLoading } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Modal states
  const [showModal, setShowModal] = useState(false);
  const [name, setName] = useState("");
  const [subject, setSubject] = useState("");
  const [course, setCourse] = useState("");
  const [semester, setSemester] = useState("");
  const [university, setUniversity] = useState("");
  const [lang, setLang] = useState("English");
  const [creating, setCreating] = useState(false);

  const router = useRouter();

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const data = await api.listProjects();
      setProjects(data);
    } catch (err: any) {
      setError(err.message || "Failed to load projects");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    } else if (user) {
      fetchProjects();
    }
  }, [user, authLoading, router]);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !subject) return;

    setCreating(true);
    try {
      const newProj = await api.createProject({
        name,
        subject,
        course: course || undefined,
        semester: semester || undefined,
        university: university || undefined,
        preferred_language: lang,
      });
      setShowModal(false);
      // Redirect straight to the syllabus uploading phase
      router.push(`/projects/${newProj.id}/syllabus`);
    } catch (err: any) {
      setError(err.message || "Failed to create project");
      setCreating(false);
    }
  };

  const handleDeleteProject = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this study project? All textbooks and notes will be permanently removed.")) {
      return;
    }

    try {
      await api.deleteProject(id);
      setProjects(projects.filter((p) => p.id !== id));
    } catch (err: any) {
      alert(err.message || "Failed to delete project");
    }
  };

  if (authLoading || loading) {
    return (
      <div className="flex-grow flex items-center justify-center bg-neutral-950">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-400" />
      </div>
    );
  }

  return (
    <div className="flex-grow flex flex-col bg-neutral-950 min-h-screen">
      {/* Top Navbar */}
      <header className="bg-neutral-900 border-b border-neutral-800 px-6 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <BookOpen className="w-5 h-5" />
          </div>
          <span className="text-xl font-bold tracking-tight text-white">
            StudyForge <span className="text-emerald-400">AI</span>
          </span>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 text-sm text-neutral-300">
            <User className="w-4 h-4 text-neutral-500" />
            <span>{user?.email}</span>
          </div>
          <button
            onClick={logout}
            className="p-2 rounded-lg text-neutral-400 hover:text-red-400 hover:bg-red-500/10 transition-all"
            title="Sign Out"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Main Workspace Dashboard */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full flex-1">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white">Your Study Projects</h1>
            <p className="text-neutral-400 text-sm mt-1">
              Create a workspace for a subject, map your syllabus, and compile reference guides.
            </p>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="inline-flex items-center px-4 py-2.5 rounded-lg bg-emerald-400 hover:bg-emerald-300 text-neutral-950 font-semibold transition-all shadow-sm self-start md:self-auto"
          >
            <Plus className="w-5 h-5 mr-1.5" />
            New Study Project
          </button>
        </div>

        {error && (
          <div className="mb-6 bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-start space-x-3 text-red-400 text-sm">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Project Cards Grid */}
        {projects.length === 0 ? (
          <div className="text-center py-20 bg-neutral-900/30 rounded-2xl border border-dashed border-neutral-800">
            <Folder className="w-12 h-12 text-neutral-700 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-1">No Projects Found</h3>
            <p className="text-neutral-500 text-sm max-w-sm mx-auto mb-6">
              You haven't configured any workspaces yet. Create your first subject project to begin.
            </p>
            <button
              onClick={() => setShowModal(true)}
              className="inline-flex items-center px-4 py-2 rounded-lg bg-neutral-900 border border-neutral-800 text-neutral-300 hover:bg-neutral-800 hover:text-white transition-all text-sm font-semibold"
            >
              Create Study Project
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project) => (
              <div
                key={project.id}
                onClick={() => router.push(`/projects/${project.id}/notes`)}
                className="bg-neutral-900 rounded-xl border border-neutral-800 p-6 hover:border-emerald-500/30 hover:scale-[1.01] active:scale-[0.99] transition-all cursor-pointer flex flex-col justify-between group shadow-md"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                      {project.subject}
                    </span>
                    <button
                      onClick={(e) => handleDeleteProject(project.id, e)}
                      className="p-1 rounded text-neutral-500 hover:text-red-400 hover:bg-red-500/10 transition-all opacity-0 group-hover:opacity-100"
                      title="Delete Workspace"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>

                  <h3 className="text-xl font-bold text-white group-hover:text-emerald-400 transition-colors mb-2">
                    {project.name}
                  </h3>

                  <div className="space-y-1 text-sm text-neutral-400">
                    {project.course && <p>Course: {project.course}</p>}
                    {project.semester && <p>Semester: {project.semester}</p>}
                    {project.university && <p>Uni: {project.university}</p>}
                  </div>
                </div>

                <div className="border-t border-neutral-800/80 mt-6 pt-4 flex items-center justify-between text-xs text-neutral-500">
                  <div className="flex items-center space-x-1">
                    <Calendar className="w-3.5 h-3.5" />
                    <span>Created {new Date(project.created_at).toLocaleDateString()}</span>
                  </div>
                  <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform text-neutral-400" />
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Creation Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-neutral-900 w-full max-w-lg rounded-xl border border-neutral-800 p-6 overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200">
            <h3 className="text-xl font-bold text-white mb-4">Create Study Project</h3>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-1">
                  Project Name *
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. DBMS Semester 3"
                  className="block w-full px-3 py-2 border border-neutral-800 rounded-lg bg-neutral-950 text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-1">
                  Subject *
                </label>
                <input
                  type="text"
                  required
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="e.g. Database Management Systems"
                  className="block w-full px-3 py-2 border border-neutral-800 rounded-lg bg-neutral-950 text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-300 mb-1">
                    Course / Degree (Optional)
                  </label>
                  <input
                    type="text"
                    value={course}
                    onChange={(e) => setCourse(e.target.value)}
                    placeholder="e.g. B.Sc. Data Science"
                    className="block w-full px-3 py-2 border border-neutral-800 rounded-lg bg-neutral-950 text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-300 mb-1">
                    Semester (Optional)
                  </label>
                  <input
                    type="text"
                    value={semester}
                    onChange={(e) => setSemester(e.target.value)}
                    placeholder="e.g. 3"
                    className="block w-full px-3 py-2 border border-neutral-800 rounded-lg bg-neutral-950 text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-1">
                  University / Board (Optional)
                </label>
                <input
                  type="text"
                  value={university}
                  onChange={(e) => setUniversity(e.target.value)}
                  placeholder="e.g. University of Mumbai"
                  className="block w-full px-3 py-2 border border-neutral-800 rounded-lg bg-neutral-950 text-white placeholder-neutral-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-300 mb-1">
                  Preferred Note Language
                </label>
                <select
                  value={lang}
                  onChange={(e) => setLang(e.target.value)}
                  className="block w-full px-3 py-2 border border-neutral-800 rounded-lg bg-neutral-950 text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 sm:text-sm"
                >
                  <option value="English">English</option>
                  <option value="Spanish">Spanish</option>
                  <option value="French">French</option>
                  <option value="German">German</option>
                  <option value="Hindi">Hindi</option>
                </select>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-neutral-800/80">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-sm font-semibold rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-300 transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="inline-flex items-center px-4 py-2 text-sm font-semibold rounded-lg bg-emerald-400 hover:bg-emerald-300 text-neutral-950 transition-all disabled:opacity-50"
                >
                  {creating && <RefreshCw className="w-4 h-4 mr-2 animate-spin" />}
                  Create Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

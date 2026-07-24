"use client";

import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { BookOpen, Sparkles, CheckCircle, FileText, Cpu, ChevronRight } from "lucide-react";

export default function Home() {
  const { user } = useAuth();

  return (
    <div className="flex-grow flex flex-col bg-neutral-950 text-neutral-100 selection:bg-emerald-500/30">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-neutral-950/80 backdrop-blur-md border-b border-neutral-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <BookOpen className="w-5 h-5" />
            </div>
            <span className="text-xl font-bold tracking-tight text-white">
              StudyForge <span className="text-emerald-400">AI</span>
            </span>
          </div>
          <nav className="flex items-center space-x-4">
            {user ? (
              <Link
                href="/dashboard"
                className="inline-flex items-center px-4 py-2 text-sm font-semibold rounded-lg bg-emerald-400 text-neutral-950 hover:bg-emerald-300 transition-all shadow-sm"
              >
                Go to Dashboard
                <ChevronRight className="w-4 h-4 ml-1" />
              </Link>
            ) : (
              <>
                <Link
                  href="/login"
                  className="px-4 py-2 text-sm font-medium text-neutral-300 hover:text-white transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  href="/signup"
                  className="inline-flex items-center px-4 py-2 text-sm font-semibold rounded-lg bg-emerald-400 text-neutral-950 hover:bg-emerald-300 transition-all shadow-sm"
                >
                  Get Started
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col justify-center">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-20 text-center">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-semibold tracking-wide border border-emerald-500/20 mb-6">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Syllabus-Aware Note Generation Platform</span>
          </div>
          
          <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight text-white mb-6 leading-tight">
            Stop Summarizing Books. <br />
            <span className="bg-gradient-to-r from-emerald-400 to-teal-300 bg-clip-text text-transparent">
              Forge Notes That Cover Your Syllabus.
            </span>
          </h1>
          
          <p className="max-w-2xl mx-auto text-lg md:text-xl text-neutral-400 mb-10 leading-relaxed">
            StudyForge AI processes your syllabus and textbooks, matches topics automatically, 
            and generates precise study guides with page-level citations.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href={user ? "/dashboard" : "/signup"}
              className="w-full sm:w-auto inline-flex items-center justify-center px-8 py-4 text-base font-semibold rounded-xl bg-emerald-400 text-neutral-950 hover:bg-emerald-300 hover:scale-[1.02] active:scale-[0.98] transition-all shadow-lg shadow-emerald-500/10"
            >
              Start Forging For Free
              <ChevronRight className="w-5 h-5 ml-1" />
            </Link>
            <Link
              href="/login"
              className="w-full sm:w-auto inline-flex items-center justify-center px-8 py-4 text-base font-semibold rounded-xl bg-neutral-900 text-neutral-200 border border-neutral-800 hover:bg-neutral-800 transition-all"
            >
              Sign In to Your Account
            </Link>
          </div>
        </div>

        {/* Features Matrix */}
        <div className="border-t border-neutral-900 bg-neutral-950/50 py-20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {/* Feature 1 */}
              <div className="bg-neutral-900/50 p-8 rounded-2xl border border-neutral-800">
                <div className="p-3 rounded-xl bg-emerald-500/10 text-emerald-400 w-fit mb-6 border border-emerald-500/20">
                  <FileText className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">Syllabus-Controlled</h3>
                <p className="text-neutral-400 text-sm leading-relaxed">
                  Upload your syllabus first. The system designs a structured research plan around your exact course skeleton, not general guesses.
                </p>
              </div>

              {/* Feature 2 */}
              <div className="bg-neutral-900/50 p-8 rounded-2xl border border-neutral-800">
                <div className="p-3 rounded-xl bg-emerald-500/10 text-emerald-400 w-fit mb-6 border border-emerald-500/20">
                  <CheckCircle className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">Page-Level Citations</h3>
                <p className="text-neutral-400 text-sm leading-relaxed">
                  Every paragraph maps to the source page in your textbooks. Hover to see the reference, click to view the actual page in context.
                </p>
              </div>

              {/* Feature 3 */}
              <div className="bg-neutral-900/50 p-8 rounded-2xl border border-neutral-800">
                <div className="p-3 rounded-xl bg-emerald-500/10 text-emerald-400 w-fit mb-6 border border-emerald-500/20">
                  <Cpu className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">Coverage Verification</h3>
                <p className="text-neutral-400 text-sm leading-relaxed">
                  The automated checker evaluates the notes against syllabus requirements and queries textbooks again to fill missing subtopics.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-neutral-900 py-8 bg-neutral-950">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-xs text-neutral-500">
          <p>© {new Date().getFullYear()} StudyForge AI. Built for academic excellence.</p>
        </div>
      </footer>
    </div>
  );
}

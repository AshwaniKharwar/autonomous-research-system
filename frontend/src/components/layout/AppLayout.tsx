import { useState, useMemo } from 'react';
import {
  Compass,
  FileQuestion,
  Plus,
  Sparkles,
} from 'lucide-react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { Button } from '../ui/button';
import { Skeleton } from '../ui/skeleton';
import { PlanReviewSection } from '../research/PlanReviewSection';
import { WavePipelineView } from '../research/WavePipelineView';
import { ReportView } from '../research/ReportView';
import { NewResearchModal } from '../research/NewResearchModal';
import { RevisePlanModal } from '../research/RevisePlanModal';
import { TaskDetailDrawer } from '../research/TaskDetailDrawer';
import { SourcesInspector } from '../research/SourcesInspector';
import { DeleteConfirmDialog } from '../research/DeleteConfirmDialog';
import { useUIStore } from '../../store/useUIStore';
import { useResearchSession } from '../../hooks/useResearchSession';

export function AppLayout() {
  const {
    activeSessionId,
    activeTab,
    sidebarOpen,
    setIsNewModalOpen,
    selectedTaskId,
    setSelectedTaskId,
  } = useUIStore();

  const [sessionToDelete, setSessionToDelete] = useState<{ id: string; query: string } | null>(null);

  const { data: session, isLoading, isError } = useResearchSession(activeSessionId);

  // Selected task object for drawer
  const selectedTask = useMemo(() => {
    if (!session || !selectedTaskId) return null;
    return (
      session.tasks.find(
        (t) => t.task_key === selectedTaskId || t.id === selectedTaskId
      ) || null
    );
  }, [session, selectedTaskId]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      {/* Collapsible Sidebar */}
      {sidebarOpen && <Sidebar />}

      {/* Main Workspace Area */}
      <main className="flex flex-1 flex-col overflow-hidden">
        <Header
          session={session ?? null}
          onDeleteClick={() => {
            if (session) {
              setSessionToDelete({ id: session.id, query: session.query });
            }
          }}
        />

        {/* Dynamic View Body */}
        <div className="flex-1 overflow-y-auto p-6 lg:p-8">
          <div className="mx-auto max-w-7xl">
            {isLoading ? (
              <div className="space-y-6 pt-4">
                <Skeleton className="h-24 w-full rounded-2xl" />
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                  <Skeleton className="lg:col-span-7 h-96 rounded-2xl" />
                  <Skeleton className="lg:col-span-5 h-96 rounded-2xl" />
                </div>
              </div>
            ) : isError ? (
              <div className="rounded-2xl border border-destructive/30 bg-destructive/10 p-8 text-center text-sm text-destructive">
                Failed to load research session details. Please check the backend connection.
              </div>
            ) : !session ? (
              /* Welcome / Empty State */
              <div className="flex min-h-[60vh] flex-col items-center justify-center text-center space-y-6 py-12">
                <div className="relative">
                  <div className="absolute -inset-1 rounded-full bg-gradient-to-r from-primary to-violet-600 opacity-20 blur-xl animate-pulse" />
                  <div className="relative flex h-20 w-20 items-center justify-center rounded-2xl bg-card border border-border shadow-xl">
                    <Compass className="h-10 w-10 text-primary" />
                  </div>
                </div>

                <div className="space-y-2 max-w-md">
                  <h2 className="text-2xl font-bold tracking-tight text-foreground">
                    Deep Autonomous Research
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    Orchestrate multi-agent deep research workflows with human plan review,
                    parallel wave execution, live source grounding, and synthesized reports.
                  </p>
                </div>

                <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
                  <Button
                    onClick={() => setIsNewModalOpen(true)}
                    className="gap-2 shadow-lg bg-primary hover:bg-primary/90 text-primary-foreground font-medium px-6 py-5 rounded-xl text-sm"
                  >
                    <Plus className="h-4 w-4" />
                    Start New Research
                  </Button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-8 max-w-3xl w-full text-left">
                  <div className="rounded-xl border border-border/80 bg-card/60 p-4 space-y-2">
                    <Sparkles className="h-5 w-5 text-amber-500" />
                    <h4 className="text-xs font-semibold text-foreground">
                      1. Plan & Architect
                    </h4>
                    <p className="text-[11px] text-muted-foreground">
                      LLM architects decompose your question into targeted, scoped subtasks with search budgets.
                    </p>
                  </div>

                  <div className="rounded-xl border border-border/80 bg-card/60 p-4 space-y-2">
                    <FileQuestion className="h-5 w-5 text-sky-500" />
                    <h4 className="text-xs font-semibold text-foreground">
                      2. Human Review & Waves
                    </h4>
                    <p className="text-[11px] text-muted-foreground">
                      Refine the plan with feedback or approve execution across dependency-ordered waves.
                    </p>
                  </div>

                  <div className="rounded-xl border border-border/80 bg-card/60 p-4 space-y-2">
                    <Compass className="h-5 w-5 text-emerald-500" />
                    <h4 className="text-xs font-semibold text-foreground">
                      3. Synthesis & Grounding
                    </h4>
                    <p className="text-[11px] text-muted-foreground">
                      Read comprehensive reports grounded in verified web citations, with 1-click Markdown export.
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              /* Active Workspace Tab Views */
              <>
                {activeTab === 'plan' && <PlanReviewSection session={session} />}
                {activeTab === 'pipeline' && <WavePipelineView session={session} />}
                {activeTab === 'report' && <ReportView session={session} />}
              </>
            )}
          </div>
        </div>
      </main>

      {/* Global Modals & Drawers */}
      <NewResearchModal />

      {session && <RevisePlanModal sessionId={session.id} />}

      <TaskDetailDrawer
        task={selectedTask}
        open={Boolean(selectedTaskId)}
        onOpenChange={(open) => {
          if (!open) setSelectedTaskId(null);
        }}
      />

      <SourcesInspector session={session ?? null} />

      <DeleteConfirmDialog
        sessionId={sessionToDelete?.id ?? null}
        queryPreview={sessionToDelete?.query}
        open={Boolean(sessionToDelete)}
        onOpenChange={(open) => {
          if (!open) setSessionToDelete(null);
        }}
      />
    </div>
  );
}

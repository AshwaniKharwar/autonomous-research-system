import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  CheckCircle2,
  ListTodo,
  Loader2,
  RefreshCw,
  Sparkles,
} from 'lucide-react';
import type { ResearchSessionResponse } from '../../api/types';
import { Button } from '../ui/button';
import { TaskCard } from './TaskCard';
import { useResearchMutations } from '../../hooks/useResearchMutations';
import { useUIStore } from '../../store/useUIStore';

interface PlanReviewSectionProps {
  session: ResearchSessionResponse;
}

export function PlanReviewSection({ session }: PlanReviewSectionProps) {
  const { startMutation } = useResearchMutations();
  const { setIsReviseModalOpen, setSelectedTaskId } = useUIStore();

  const isPending = session.status === 'PENDING_APPROVAL';

  const handleStart = () => {
    startMutation.mutate(session.id);
  };

  return (
    <div className="space-y-6">
      {/* Human-in-the-loop Approval Banner */}
      {isPending && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 rounded-2xl border border-amber-500/30 bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-transparent p-5 backdrop-blur-sm">
          <div className="space-y-1">
            <div className="flex items-center gap-2 text-amber-500 font-semibold text-sm">
              <Sparkles className="h-4 w-4" />
              <span>Human Approval Required</span>
            </div>
            <p className="text-sm text-foreground/90">
              The AI planner synthesized this research plan and decomposed it into{' '}
              <strong className="text-foreground">{session.tasks.length} subtasks</strong>.
              Review the breakdown below and choose to approve execution or request revisions.
            </p>
          </div>

          <div className="flex items-center gap-2.5 w-full sm:w-auto">
            <Button
              variant="outline"
              onClick={() => setIsReviseModalOpen(true)}
              className="gap-2 border-amber-500/30 hover:bg-amber-500/10 flex-1 sm:flex-initial"
            >
              <RefreshCw className="h-4 w-4 text-amber-500" />
              Revise Plan
            </Button>
            <Button
              onClick={handleStart}
              disabled={startMutation.isPending}
              className="gap-2 bg-emerald-600 hover:bg-emerald-700 text-white flex-1 sm:flex-initial"
            >
              {startMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Starting Waves...
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4" />
                  Approve & Start
                </>
              )}
            </Button>
          </div>
        </div>
      )}

      {/* Plan Document & Subtasks Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Markdown Plan Document */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              Synthesized Research Plan
            </h3>
          </div>

          <div className="rounded-2xl border border-border/80 bg-card p-6 shadow-sm">
            {session.plan?.content ? (
              <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:font-semibold prose-headings:tracking-tight prose-a:text-primary">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {session.plan.content}
                </ReactMarkdown>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground italic">
                No plan content generated yet.
              </p>
            )}
          </div>
        </div>

        {/* Right Column: Architected Subtasks */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <ListTodo className="h-4 w-4 text-primary" />
              Subtasks Architecture ({session.tasks.length})
            </h3>
            <span className="text-xs text-muted-foreground">Click task for details</span>
          </div>

          <div className="space-y-3">
            {session.tasks.map((task) => (
              <TaskCard
                key={task.id}
                task={task}
                onClick={() => setSelectedTaskId(task.task_key)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

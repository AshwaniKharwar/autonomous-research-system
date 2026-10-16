import { useMemo } from 'react';
import {
  AlertOctagon,
  CheckCircle2,
  Cpu,
  Layers,
  Loader2,
} from 'lucide-react';
import type { ResearchSessionResponse, ResearchTaskResponse } from '../../api/types';
import { Button } from '../ui/button';
import { TaskCard } from './TaskCard';
import { DispatchLogTimeline } from './DispatchLogTimeline';
import { useResearchMutations } from '../../hooks/useResearchMutations';
import { useUIStore } from '../../store/useUIStore';

interface WavePipelineViewProps {
  session: ResearchSessionResponse;
}

export function WavePipelineView({ session }: WavePipelineViewProps) {
  const { cancelMutation } = useResearchMutations();
  const { setSelectedTaskId } = useUIStore();

  const isRunning = session.status === 'RUNNING';

  // Group tasks by wave
  const wavesMap = useMemo(() => {
    const map = new Map<number, ResearchTaskResponse[]>();
    for (const task of session.tasks) {
      const waveNum = task.wave ?? 1;
      if (!map.has(waveNum)) {
        map.set(waveNum, []);
      }
      map.get(waveNum)!.push(task);
    }
    // Return sorted by wave number
    return Array.from(map.entries()).sort(([a], [b]) => a - b);
  }, [session.tasks]);

  const completedCount = session.tasks.filter((t) => t.status === 'COMPLETED').length;
  const progressPercent = session.tasks.length > 0
    ? Math.round((completedCount / session.tasks.length) * 100)
    : 0;

  return (
    <div className="space-y-6">
      {/* Wave Execution Progress Bar & Controls */}
      <div className="rounded-2xl border border-border/80 bg-card p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="flex h-2 w-2 rounded-full bg-primary animate-pulse" />
              <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
                <Cpu className="h-4 w-4 text-primary" />
                Multi-Agent Wave Pipeline
              </h3>
            </div>
            <p className="text-xs text-muted-foreground">
              Tasks execute concurrently in dependency-ordered waves. Subtask findings feed directly
              into subsequent waves and the final synthesis report.
            </p>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto justify-between sm:justify-end">
            <div className="text-right">
              <span className="text-xs font-semibold text-foreground">
                {completedCount} of {session.tasks.length} Completed
              </span>
              <span className="text-[11px] text-muted-foreground block">
                {progressPercent}% Total Progress
              </span>
            </div>

            {isRunning && (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => cancelMutation.mutate(session.id)}
                disabled={cancelMutation.isPending}
                className="gap-1.5"
              >
                {cancelMutation.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <AlertOctagon className="h-3.5 w-3.5" />
                )}
                Cancel Execution
              </Button>
            )}
          </div>
        </div>

        {/* Progress Line */}
        <div className="h-2 w-full rounded-full bg-secondary overflow-hidden">
          <div
            className="h-full bg-primary transition-all duration-500 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Main Grid: Wave Lanes (Left) + Dispatch Log Feed (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Wave Lanes */}
        <div className="lg:col-span-8 space-y-6">
          {wavesMap.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border p-12 text-center text-xs text-muted-foreground">
              No tasks assigned to waves yet.
            </div>
          ) : (
            wavesMap.map(([waveNum, waveTasks]) => {
              const waveCompleted = waveTasks.every((t) => t.status === 'COMPLETED');
              const waveRunning = waveTasks.some((t) => t.status === 'RUNNING');

              return (
                <div
                  key={waveNum}
                  className="rounded-2xl border border-border/80 bg-card/60 backdrop-blur-sm p-5 space-y-4 shadow-sm"
                >
                  <div className="flex items-center justify-between pb-2 border-b border-border/60">
                    <div className="flex items-center gap-2">
                      <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10 text-primary font-semibold text-xs">
                        W{waveNum}
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-foreground">
                          Wave {waveNum} Tasks
                        </h4>
                        <span className="text-[11px] text-muted-foreground">
                          {waveTasks.length} parallel research agents
                        </span>
                      </div>
                    </div>

                    <div>
                      {waveCompleted ? (
                        <span className="inline-flex items-center gap-1 text-xs text-emerald-500 font-medium">
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          Wave Complete
                        </span>
                      ) : waveRunning ? (
                        <span className="inline-flex items-center gap-1 text-xs text-sky-500 font-medium animate-pulse">
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          Executing Wave
                        </span>
                      ) : (
                        <span className="text-xs text-muted-foreground">
                          Queued
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {waveTasks.map((task) => (
                      <TaskCard
                        key={task.id}
                        task={task}
                        onClick={() => setSelectedTaskId(task.task_key)}
                      />
                    ))}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Dispatch Log Feed */}
        <div className="lg:col-span-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Layers className="h-4 w-4 text-primary" />
              Live Agent Activity
            </h3>
          </div>
          <DispatchLogTimeline logs={session.dispatch_logs} />
        </div>
      </div>
    </div>
  );
}

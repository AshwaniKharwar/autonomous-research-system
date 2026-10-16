import { Activity, Clock, Terminal } from 'lucide-react';
import type { DispatchLogResponse } from '../../api/types';
import { formatDate } from '../../utils/formatters';

interface DispatchLogTimelineProps {
  logs: DispatchLogResponse[];
}

export function DispatchLogTimeline({ logs }: DispatchLogTimelineProps) {
  if (!logs || logs.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border/80 p-8 text-center text-xs text-muted-foreground flex flex-col items-center justify-center gap-2">
        <Terminal className="h-6 w-6 text-muted-foreground/50" />
        <span>No dispatch logs recorded yet. Execution logs will stream here.</span>
      </div>
    );
  }

  // Sort logs by created_at ascending
  const sortedLogs = [...logs].sort((a, b) => {
    const timeA = a.created_at ? new Date(a.created_at).getTime() : 0;
    const timeB = b.created_at ? new Date(b.created_at).getTime() : 0;
    return timeA - timeB;
  });

  return (
    <div className="rounded-xl border border-border/80 bg-secondary/20 p-4 space-y-3 font-mono text-xs">
      <div className="flex items-center justify-between pb-2 border-b border-border/60">
        <span className="text-muted-foreground flex items-center gap-1.5 font-sans font-semibold uppercase tracking-wider text-[11px]">
          <Activity className="h-3.5 w-3.5 text-primary" />
          Dispatch Activity Feed ({logs.length})
        </span>
      </div>

      <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
        {sortedLogs.map((log) => {
          const isCompleted = log.status.toUpperCase() === 'COMPLETED';
          const isRunning = log.status.toUpperCase() === 'RUNNING';
          const isFailed = log.status.toUpperCase() === 'FAILED';

          return (
            <div
              key={log.id}
              className="flex items-start gap-2.5 rounded-lg border border-border/60 bg-card/60 p-2.5 transition-colors hover:bg-card"
            >
              <span
                className={`mt-0.5 inline-block h-2 w-2 rounded-full flex-shrink-0 ${
                  isCompleted
                    ? 'bg-emerald-500'
                    : isRunning
                    ? 'bg-sky-500 animate-ping'
                    : isFailed
                    ? 'bg-rose-500'
                    : 'bg-muted-foreground'
                }`}
              />

              <div className="flex-1 space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold text-foreground">
                    Wave {log.wave} • {log.task_key}
                  </span>
                  <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                    <Clock className="h-2.5 w-2.5" />
                    {formatDate(log.created_at)}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] uppercase font-semibold px-1.5 py-0.2 rounded ${
                      isCompleted
                        ? 'bg-emerald-500/10 text-emerald-500'
                        : isRunning
                        ? 'bg-sky-500/10 text-sky-500'
                        : isFailed
                        ? 'bg-rose-500/10 text-rose-500'
                        : 'bg-secondary text-muted-foreground'
                    }`}
                  >
                    {log.status}
                  </span>
                  {log.note && (
                    <span className="text-muted-foreground line-clamp-1">
                      {log.note}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

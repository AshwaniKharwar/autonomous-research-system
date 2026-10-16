import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  ExternalLink,
  Globe,
  HelpCircle,
  Network,
  Search,
  Sparkles,
} from 'lucide-react';
import type { ResearchTaskResponse } from '../../api/types';
import {
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from '../ui/drawer';
import { StatusBadge } from './StatusBadge';
import { Badge } from '../ui/badge';

interface TaskDetailDrawerProps {
  task: ResearchTaskResponse | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function TaskDetailDrawer({
  task,
  open,
  onOpenChange,
}: TaskDetailDrawerProps) {
  if (!task) return null;

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="max-w-2xl sm:max-w-2xl">
        <DrawerHeader>
          <div className="flex items-center justify-between gap-3 pr-6">
            <span className="font-mono text-xs font-semibold uppercase tracking-wider text-primary">
              {task.task_key}
            </span>
            <StatusBadge status={task.status} />
          </div>
          <DrawerTitle className="text-xl pt-1 leading-snug">
            {task.title}
          </DrawerTitle>
          {task.angle && (
            <DrawerDescription className="italic text-foreground/80">
              Angle: &quot;{task.angle}&quot;
            </DrawerDescription>
          )}
        </DrawerHeader>

        <DrawerBody className="space-y-6 divide-y divide-border/60">
          {/* Metadata & Config */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2 text-xs">
            <div className="rounded-lg border border-border/80 bg-secondary/30 p-2.5">
              <span className="text-muted-foreground block text-[11px]">Wave</span>
              <span className="font-semibold text-foreground text-sm">
                {task.wave ?? 'Auto'}
              </span>
            </div>
            <div className="rounded-lg border border-border/80 bg-secondary/30 p-2.5">
              <span className="text-muted-foreground block text-[11px] flex items-center gap-1">
                <Search className="h-3 w-3" />
                Search Budget
              </span>
              <span className="font-semibold text-foreground text-sm">
                {task.search_budget} queries
              </span>
            </div>
            <div className="rounded-lg border border-border/80 bg-secondary/30 p-2.5 col-span-2 sm:col-span-1">
              <span className="text-muted-foreground block text-[11px]">Min Sources</span>
              <span className="font-semibold text-foreground text-sm">
                {task.min_sources} sources
              </span>
            </div>
          </div>

          {/* Research Questions */}
          {task.questions && task.questions.length > 0 && (
            <div className="pt-5 space-y-2.5">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <HelpCircle className="h-4 w-4 text-primary" />
                Target Questions
              </h4>
              <ul className="space-y-1.5 pl-2">
                {task.questions.map((q, idx) => (
                  <li key={idx} className="text-sm text-foreground/90 flex gap-2">
                    <span className="text-primary font-mono text-xs">{idx + 1}.</span>
                    <span>{q}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Scope & Context */}
          {(task.scope || task.context) && (
            <div className="pt-5 space-y-3">
              {task.scope && (
                <div className="space-y-1">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Scope
                  </h4>
                  <p className="text-sm text-muted-foreground">{task.scope}</p>
                </div>
              )}
              {task.context && (
                <div className="space-y-1">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Context
                  </h4>
                  <p className="text-sm text-muted-foreground">{task.context}</p>
                </div>
              )}
            </div>
          )}

          {/* Dependencies */}
          {task.depends_on && task.depends_on.length > 0 && (
            <div className="pt-5 space-y-2">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Network className="h-4 w-4 text-primary" />
                Dependencies
              </h4>
              <div className="flex flex-wrap gap-2">
                {task.depends_on.map((dep) => (
                  <Badge key={dep} variant="outline" className="font-mono text-xs">
                    {dep}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Research Findings */}
          <div className="pt-5 space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Sparkles className="h-4 w-4 text-primary" />
              Agent Findings
            </h4>
            {task.findings ? (
              <div className="prose prose-sm dark:prose-invert max-w-none rounded-xl border border-border/80 bg-secondary/20 p-4">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {task.findings}
                </ReactMarkdown>
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
                Findings will appear here once the agent finishes research on this task.
              </div>
            )}
          </div>

          {/* Sources Collected */}
          <div className="pt-5 space-y-3 pb-4">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Globe className="h-4 w-4 text-emerald-500" />
              Sources Gathered ({task.sources?.length || 0})
            </h4>

            {task.sources && task.sources.length > 0 ? (
              <div className="space-y-2">
                {task.sources.map((src, i) => (
                  <div
                    key={i}
                    className="group rounded-lg border border-border/70 bg-card p-3 hover:border-border transition-colors text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium text-foreground line-clamp-1">
                        {src.title || src.url || `Source #${i + 1}`}
                      </span>
                      {src.url && (
                        <a
                          href={src.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-primary hover:underline flex items-center gap-1 text-[11px]"
                        >
                          Visit
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                    </div>
                    {src.snippet && (
                      <p className="text-muted-foreground line-clamp-2">
                        {src.snippet}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground italic">
                No external sources logged yet for this task.
              </p>
            )}
          </div>
        </DrawerBody>
      </DrawerContent>
    </Drawer>
  );
}

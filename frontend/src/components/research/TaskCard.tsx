import {
  FileText,
  Globe,
  HelpCircle,
  Network,
  Search,
} from 'lucide-react';
import type { ResearchTaskResponse } from '../../api/types';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { StatusBadge } from './StatusBadge';
import { cn } from '../../utils/cn';
import { Badge } from '../ui/badge';

interface TaskCardProps {
  task: ResearchTaskResponse;
  onClick?: () => void;
  className?: string;
}

export function TaskCard({ task, onClick, className }: TaskCardProps) {
  const isRunning = task.status === 'RUNNING';

  return (
    <Card
      onClick={onClick}
      className={cn(
        'group cursor-pointer border border-border/80 bg-card/60 backdrop-blur-sm transition-all hover:border-primary/50 hover:shadow-md hover:-translate-y-0.5',
        isRunning && 'ring-1 ring-primary/40 shadow-sm border-primary/40',
        className
      )}
    >
      <CardHeader className="p-4 pb-2">
        <div className="flex items-center justify-between gap-2">
          <span className="font-mono text-xs font-semibold uppercase tracking-wider text-muted-foreground group-hover:text-primary transition-colors">
            {task.task_key}
          </span>
          <StatusBadge status={task.status} />
        </div>
        <CardTitle className="text-sm font-medium leading-snug line-clamp-2 pt-1 group-hover:text-primary transition-colors">
          {task.title}
        </CardTitle>
      </CardHeader>

      <CardContent className="p-4 pt-1 space-y-3">
        {task.angle && (
          <p className="text-xs text-muted-foreground line-clamp-2 italic">
            &quot;{task.angle}&quot;
          </p>
        )}

        <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-muted-foreground">
          {task.questions && task.questions.length > 0 && (
            <span className="flex items-center gap-1">
              <HelpCircle className="h-3 w-3 text-muted-foreground/70" />
              {task.questions.length} questions
            </span>
          )}

          <span className="flex items-center gap-1">
            <Search className="h-3 w-3 text-muted-foreground/70" />
            Budget: {task.search_budget}
          </span>

          {task.sources && task.sources.length > 0 && (
            <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
              <Globe className="h-3 w-3" />
              {task.sources.length} sources
            </span>
          )}

          {task.findings && (
            <span className="flex items-center gap-1 text-sky-600 dark:text-sky-400 font-medium">
              <FileText className="h-3 w-3" />
              Findings ready
            </span>
          )}
        </div>

        {task.depends_on && task.depends_on.length > 0 && (
          <div className="flex items-center gap-1.5 pt-1 border-t border-border/50 text-[11px] text-muted-foreground">
            <Network className="h-3 w-3 text-muted-foreground/70" />
            <span>Depends on:</span>
            <div className="flex flex-wrap gap-1">
              {task.depends_on.map((dep) => (
                <Badge
                  key={dep}
                  variant="outline"
                  className="px-1.5 py-0 text-[10px] font-mono"
                >
                  {dep}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

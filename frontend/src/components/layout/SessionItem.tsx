import { Trash2 } from 'lucide-react';
import type { ResearchSessionResponse } from '../../api/types';
import { StatusBadge } from '../research/StatusBadge';
import { formatRelativeTime } from '../../utils/formatters';
import { cn } from '../../utils/cn';

interface SessionItemProps {
  session: ResearchSessionResponse;
  isActive: boolean;
  onSelect: () => void;
  onDeleteClick: (e: React.MouseEvent) => void;
}

export function SessionItem({
  session,
  isActive,
  onSelect,
  onDeleteClick,
}: SessionItemProps) {
  return (
    <div
      onClick={onSelect}
      className={cn(
        'group relative flex flex-col gap-1.5 rounded-xl p-3 text-left transition-all cursor-pointer border',
        isActive
          ? 'bg-secondary/80 border-border shadow-xs'
          : 'border-transparent hover:bg-secondary/40 hover:border-border/50'
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] text-muted-foreground font-mono">
          {formatRelativeTime(session.created_at)}
        </span>
        <div className="flex items-center gap-1.5">
          <StatusBadge status={session.status} showIcon={false} className="text-[10px] px-1.5 py-0" />
          <button
            type="button"
            onClick={onDeleteClick}
            className="opacity-0 group-hover:opacity-100 p-1 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all"
            title="Delete session"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </div>
      </div>

      <p className="text-xs font-medium text-foreground line-clamp-2 leading-snug">
        {session.query}
      </p>

      {session.tasks && session.tasks.length > 0 && (
        <span className="text-[10px] text-muted-foreground">
          {session.tasks.length} subtasks
        </span>
      )}
    </div>
  );
}

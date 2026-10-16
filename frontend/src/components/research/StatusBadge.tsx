import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Loader2,
  XCircle,
} from 'lucide-react';
import type { ResearchStatus, TaskStatus } from '../../api/types';
import { Badge } from '../ui/badge';
import { cn } from '../../utils/cn';

interface StatusBadgeProps {
  status: ResearchStatus | TaskStatus;
  className?: string;
  showIcon?: boolean;
}

export function StatusBadge({
  status,
  className,
  showIcon = true,
}: StatusBadgeProps) {
  switch (status) {
    case 'PENDING_APPROVAL':
      return (
        <Badge
          variant="warning"
          className={cn('gap-1 font-medium', className)}
        >
          {showIcon && <Clock className="h-3 w-3" />}
          Pending Approval
        </Badge>
      );
    case 'RUNNING':
      return (
        <Badge
          variant="info"
          className={cn('gap-1 font-medium animate-pulse', className)}
        >
          {showIcon && <Loader2 className="h-3 w-3 animate-spin" />}
          Running
        </Badge>
      );
    case 'COMPLETED':
      return (
        <Badge
          variant="success"
          className={cn('gap-1 font-medium', className)}
        >
          {showIcon && <CheckCircle2 className="h-3 w-3" />}
          Completed
        </Badge>
      );
    case 'FAILED':
      return (
        <Badge
          variant="destructive"
          className={cn('gap-1 font-medium', className)}
        >
          {showIcon && <AlertCircle className="h-3 w-3" />}
          Failed
        </Badge>
      );
    case 'CANCELLED':
      return (
        <Badge
          variant="secondary"
          className={cn('gap-1 font-medium opacity-80', className)}
        >
          {showIcon && <XCircle className="h-3 w-3" />}
          Cancelled
        </Badge>
      );
    case 'PENDING':
      return (
        <Badge
          variant="outline"
          className={cn('gap-1 text-muted-foreground', className)}
        >
          {showIcon && <Clock className="h-3 w-3" />}
          Pending
        </Badge>
      );
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

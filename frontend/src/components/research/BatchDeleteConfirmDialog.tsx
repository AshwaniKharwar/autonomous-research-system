import { AlertTriangle, Loader2, Trash2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { useResearchMutations } from '../../hooks/useResearchMutations';
import type { ResearchStatus } from '../../api/types';

interface BatchDeleteConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedSessions: Array<{ id: string; query: string; status: ResearchStatus }>;
  onSuccess?: () => void;
}

export function BatchDeleteConfirmDialog({
  open,
  onOpenChange,
  selectedSessions,
  onSuccess,
}: BatchDeleteConfirmDialogProps) {
  const { batchDeleteMutation } = useResearchMutations();

  const count = selectedSessions.length;
  const runningCount = selectedSessions.filter((s) => s.status === 'RUNNING').length;

  const handleBatchDelete = () => {
    if (count === 0) return;
    const ids = selectedSessions.map((s) => s.id);
    batchDeleteMutation.mutate(ids, {
      onSuccess: () => {
        onOpenChange(false);
        onSuccess?.();
      },
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2 text-destructive font-medium text-sm">
            <Trash2 className="h-4 w-4" />
            <span>Confirm Batch Deletion</span>
          </div>
          <DialogTitle className="text-xl">
            Delete {count} Research {count === 1 ? 'Session' : 'Sessions'}
          </DialogTitle>
          <DialogDescription>
            Are you sure you want to permanently delete {count === 1 ? 'this' : 'these'}{' '}
            {count} research {count === 1 ? 'session' : 'sessions'}? This action cannot be
            undone and will remove all corresponding subtasks, findings, logs, and reports.
          </DialogDescription>
        </DialogHeader>

        {runningCount > 0 && (
          <div className="flex items-start gap-2.5 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-500">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Active execution in progress</p>
              <p className="text-muted-foreground mt-0.5">
                {runningCount} of the selected {runningCount === 1 ? 'session is' : 'sessions are'} currently
                running. Deleting will immediately abort and cancel background research execution.
              </p>
            </div>
          </div>
        )}

        {/* Selected items preview */}
        <div className="space-y-1.5 max-h-48 overflow-y-auto rounded-lg border border-border bg-muted/30 p-2.5">
          <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider px-1">
            Selected for deletion ({count})
          </p>
          <div className="space-y-1">
            {selectedSessions.map((s) => (
              <div
                key={s.id}
                className="flex items-center justify-between gap-2 rounded-md bg-card/60 px-2.5 py-1.5 text-xs text-foreground border border-border/50"
              >
                <span className="truncate max-w-[280px]" title={s.query}>
                  {s.query}
                </span>
                {s.status === 'RUNNING' && (
                  <span className="text-[10px] px-1.5 py-0.2 rounded font-medium bg-amber-500/15 text-amber-500 shrink-0">
                    Running
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>

        <DialogFooter className="pt-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={batchDeleteMutation.isPending}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={handleBatchDelete}
            disabled={batchDeleteMutation.isPending || count === 0}
            className="gap-2"
          >
            {batchDeleteMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Deleting {count}...
              </>
            ) : (
              `Delete ${count} ${count === 1 ? 'Session' : 'Sessions'}`
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

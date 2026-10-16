import { Trash2, Loader2 } from 'lucide-react';
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

interface DeleteConfirmDialogProps {
  sessionId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  queryPreview?: string;
}

export function DeleteConfirmDialog({
  sessionId,
  open,
  onOpenChange,
  queryPreview,
}: DeleteConfirmDialogProps) {
  const { deleteMutation } = useResearchMutations();

  const handleDelete = () => {
    if (!sessionId) return;
    deleteMutation.mutate(sessionId, {
      onSuccess: () => {
        onOpenChange(false);
      },
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2 text-destructive font-medium text-sm">
            <Trash2 className="h-4 w-4" />
            <span>Confirm Deletion</span>
          </div>
          <DialogTitle className="text-xl">Delete Research Session</DialogTitle>
          <DialogDescription>
            Are you sure you want to permanently delete this research session? This action
            cannot be undone and will remove all tasks, findings, logs, and compiled reports.
          </DialogDescription>
        </DialogHeader>

        {queryPreview && (
          <div className="rounded-lg border border-border bg-muted/40 p-3 text-xs text-foreground font-mono truncate">
            &quot;{queryPreview}&quot;
          </div>
        )}

        <DialogFooter className="pt-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={deleteMutation.isPending}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
            className="gap-2"
          >
            {deleteMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Deleting...
              </>
            ) : (
              'Delete Permanently'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

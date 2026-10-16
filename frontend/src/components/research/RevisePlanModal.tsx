import { useState } from 'react';
import { RefreshCw, Loader2, MessageSquarePlus } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Textarea } from '../ui/textarea';
import { useUIStore } from '../../store/useUIStore';
import { useResearchMutations } from '../../hooks/useResearchMutations';

const REVISION_CHIPS = [
  'Focus more on real-world benchmarks and performance numbers',
  'Add competitive comparison with leading alternatives',
  'Deep dive into potential architectural security risks',
  'Include open-source tools and self-hosted options',
];

interface RevisePlanModalProps {
  sessionId: string;
}

export function RevisePlanModal({ sessionId }: RevisePlanModalProps) {
  const { isReviseModalOpen, setIsReviseModalOpen } = useUIStore();
  const { reviseMutation } = useResearchMutations();
  const [feedback, setFeedback] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = feedback.trim();
    if (trimmed.length < 3) return;

    reviseMutation.mutate(
      {
        id: sessionId,
        data: { feedback: trimmed },
      },
      {
        onSuccess: () => {
          setFeedback('');
        },
      }
    );
  };

  const handleChipClick = (chip: string) => {
    setFeedback((prev) => (prev ? `${prev}. ${chip}` : chip));
  };

  return (
    <Dialog open={isReviseModalOpen} onOpenChange={setIsReviseModalOpen}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <div className="flex items-center gap-2 text-amber-500 font-medium text-sm">
            <RefreshCw className="h-4 w-4" />
            <span>Human-in-the-Loop Refinement</span>
          </div>
          <DialogTitle className="text-xl">Revise Research Plan</DialogTitle>
          <DialogDescription>
            Provide feedback or adjustments. The research planner and architect will update
            the plan and restructure the subtasks accordingly.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          <div className="space-y-2">
            <label
              htmlFor="revision-feedback"
              className="text-xs font-semibold uppercase tracking-wider text-muted-foreground"
            >
              Revision Feedback & Directions
            </label>
            <Textarea
              id="revision-feedback"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="e.g. Please add an extra task focusing on enterprise pricing and customer sentiment..."
              rows={4}
              className="resize-none"
              disabled={reviseMutation.isPending}
              autoFocus
            />
            <div className="flex justify-between items-center text-xs text-muted-foreground">
              <span>Minimum 3 characters</span>
              <span>{feedback.length} chars</span>
            </div>
          </div>

          <div className="space-y-2 pt-1">
            <span className="text-xs font-medium text-muted-foreground flex items-center gap-1">
              <MessageSquarePlus className="h-3.5 w-3.5" />
              Quick directions:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {REVISION_CHIPS.map((chip, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleChipClick(chip)}
                  disabled={reviseMutation.isPending}
                  className="rounded-full border border-border/80 bg-secondary/40 px-2.5 py-1 text-xs text-secondary-foreground hover:bg-secondary transition-colors text-left"
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>

          {reviseMutation.isError && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
              {reviseMutation.error instanceof Error
                ? reviseMutation.error.message
                : 'Failed to revise plan'}
            </div>
          )}

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsReviseModalOpen(false)}
              disabled={reviseMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={feedback.trim().length < 3 || reviseMutation.isPending}
              className="gap-2 bg-amber-600 hover:bg-amber-700 text-white"
            >
              {reviseMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Re-architecting Plan & Tasks...
                </>
              ) : (
                <>
                  Apply Revisions
                  <RefreshCw className="h-4 w-4" />
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

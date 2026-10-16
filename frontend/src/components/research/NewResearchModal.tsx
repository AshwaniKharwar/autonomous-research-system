import { useState } from 'react';
import { Sparkles, Loader2, ArrowRight } from 'lucide-react';
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

const SAMPLE_PROMPTS = [
  'Emerging multi-agent AI frameworks and orchestration architectures in 2026',
  'PostgreSQL performance optimizations for vector search and high concurrency',
  'Comparison of lightweight browser runtimes: Bun vs Node.js vs Deno',
  'Autonomous coding agent safety guardrails and sandboxing techniques',
];

export function NewResearchModal() {
  const { isNewModalOpen, setIsNewModalOpen } = useUIStore();
  const { createMutation } = useResearchMutations();
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (trimmed.length < 5) return;

    createMutation.mutate(
      { query: trimmed },
      {
        onSuccess: () => {
          setQuery('');
        },
      }
    );
  };

  const handleSelectPrompt = (prompt: string) => {
    setQuery(prompt);
  };

  return (
    <Dialog open={isNewModalOpen} onOpenChange={setIsNewModalOpen}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <div className="flex items-center gap-2 text-primary font-medium text-sm">
            <Sparkles className="h-4 w-4" />
            <span>Multi-Agent Research Assistant</span>
          </div>
          <DialogTitle className="text-xl">Start New Deep Research</DialogTitle>
          <DialogDescription>
            Enter your research question or topic. The system will synthesize an in-depth
            plan and architect subtasks for your approval.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          <div className="space-y-2">
            <label
              htmlFor="research-query"
              className="text-xs font-semibold uppercase tracking-wider text-muted-foreground"
            >
              Research Topic or Question
            </label>
            <Textarea
              id="research-query"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. In-depth analysis of modern WebAssembly compilers and runtime performance..."
              rows={4}
              className="resize-none"
              disabled={createMutation.isPending}
              autoFocus
            />
            <div className="flex justify-between items-center text-xs text-muted-foreground">
              <span>Minimum 5 characters</span>
              <span>{query.length} chars</span>
            </div>
          </div>

          <div className="space-y-2 pt-1">
            <span className="text-xs font-medium text-muted-foreground">
              Suggested topics:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {SAMPLE_PROMPTS.map((prompt, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleSelectPrompt(prompt)}
                  disabled={createMutation.isPending}
                  className="rounded-full border border-border/80 bg-secondary/40 px-2.5 py-1 text-xs text-secondary-foreground hover:bg-secondary transition-colors text-left"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          {createMutation.isError && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
              {createMutation.error instanceof Error
                ? createMutation.error.message
                : 'Failed to create research plan'}
            </div>
          )}

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsNewModalOpen(false)}
              disabled={createMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={query.trim().length < 5 || createMutation.isPending}
              className="gap-2"
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generating Plan & Tasks...
                </>
              ) : (
                <>
                  Generate Plan
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

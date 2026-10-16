import { useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  BookOpen,
  Check,
  Clock,
  Copy,
  Download,
  FileText,
  Globe,
  Sparkles,
} from 'lucide-react';
import type { ResearchSessionResponse } from '../../api/types';
import { Button } from '../ui/button';
import { copyToClipboard, downloadMarkdown } from '../../utils/export';
import { useUIStore } from '../../store/useUIStore';

interface ReportViewProps {
  session: ResearchSessionResponse;
}

interface TocItem {
  id: string;
  text: string;
  level: number;
}

export function ReportView({ session }: ReportViewProps) {
  const { setIsSourcesDrawerOpen } = useUIStore();
  const [copied, setCopied] = useState(false);

  const report = session.report;
  const content = report?.content || '';

  // Calculate total sources count
  const totalSourcesCount = useMemo(() => {
    return session.tasks.reduce((sum, t) => sum + (t.sources?.length || 0), 0);
  }, [session.tasks]);

  // Extract Table of Contents from Markdown headings
  const toc = useMemo<TocItem[]>(() => {
    if (!content) return [];
    const lines = content.split('\n');
    const items: TocItem[] = [];

    for (const line of lines) {
      const match = line.match(/^(#{2,3})\s+(.*)$/);
      if (match) {
        const level = match[1].length;
        const text = match[2].trim().replace(/\*\*/g, '');
        const id = text
          .toLowerCase()
          .replace(/[^\w\s-]/g, '')
          .replace(/\s+/g, '-');
        items.push({ id, text, level });
      }
    }

    return items;
  }, [content]);

  const handleCopy = async () => {
    if (!content) return;
    const success = await copyToClipboard(content);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownload = () => {
    if (!content) return;
    const safeTitle = (session.plan?.title || session.query || 'research-report')
      .slice(0, 50)
      .replace(/[^a-zA-Z0-9_-]/g, '_');
    downloadMarkdown(safeTitle, content);
  };

  if (!report || !content) {
    return (
      <div className="rounded-2xl border border-dashed border-border p-12 text-center space-y-3">
        <FileText className="h-10 w-10 text-muted-foreground/40 mx-auto" />
        <h3 className="text-base font-semibold text-foreground">
          Report Not Ready Yet
        </h3>
        <p className="text-xs text-muted-foreground max-w-md mx-auto">
          The comprehensive research report will be synthesized automatically once all
          subtask waves complete.
        </p>
      </div>
    );
  }

  const wordCount = report.word_count || content.split(/\s+/).length;
  const readTimeMin = Math.max(1, Math.round(wordCount / 200));

  return (
    <div className="space-y-6">
      {/* Header & Export Actions Toolbar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 rounded-2xl border border-border/80 bg-card p-5 shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-primary font-semibold text-sm">
            <Sparkles className="h-4 w-4" />
            <span>Final Synthesized Research Report</span>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground pt-0.5">
            <span className="flex items-center gap-1">
              <FileText className="h-3.5 w-3.5" />
              {wordCount.toLocaleString()} words
            </span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              ~{readTimeMin} min read
            </span>
            <span>•</span>
            <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
              <Globe className="h-3.5 w-3.5" />
              {totalSourcesCount} grounded sources
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsSourcesDrawerOpen(true)}
            className="gap-1.5"
          >
            <Globe className="h-3.5 w-3.5 text-emerald-500" />
            Sources ({totalSourcesCount})
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleCopy}
            className="gap-1.5"
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-500" />
                Copied
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5" />
                Copy
              </>
            )}
          </Button>

          <Button
            size="sm"
            onClick={handleDownload}
            className="gap-1.5 bg-primary hover:bg-primary/90"
          >
            <Download className="h-3.5 w-3.5" />
            Export (.md)
          </Button>
        </div>
      </div>

      {/* Main Grid: Markdown Prose (Left) + Table of Contents (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Report Content */}
        <div className="lg:col-span-8 xl:col-span-9 rounded-2xl border border-border/80 bg-card p-8 sm:p-10 shadow-sm">
          <article className="prose prose-zinc dark:prose-invert max-w-none prose-headings:font-semibold prose-headings:tracking-tight prose-h1:text-2xl sm:prose-h1:text-3xl prose-h2:text-xl prose-h2:mt-8 prose-h2:border-b prose-h2:border-border/60 prose-h2:pb-2 prose-a:text-primary prose-a:underline-offset-4 prose-blockquote:border-l-primary prose-code:font-mono prose-code:text-primary prose-pre:bg-secondary/60 prose-pre:border prose-pre:border-border">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
          </article>
        </div>

        {/* Sticky Table of Contents Sidebar */}
        <div className="hidden lg:block lg:col-span-4 xl:col-span-3 sticky top-6 space-y-4">
          <div className="rounded-2xl border border-border/80 bg-card p-5 shadow-sm space-y-3">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground pb-1 border-b border-border/60">
              <BookOpen className="h-3.5 w-3.5 text-primary" />
              <span>Report Outline</span>
            </div>

            {toc.length === 0 ? (
              <p className="text-xs text-muted-foreground italic">
                No section headings found.
              </p>
            ) : (
              <nav className="space-y-1.5 max-h-[70vh] overflow-y-auto pr-1 text-xs">
                {toc.map((item, idx) => (
                  <a
                    key={idx}
                    href={`#${item.id}`}
                    className={`block py-1 text-muted-foreground hover:text-foreground transition-colors truncate ${
                      item.level === 3 ? 'pl-4 text-[11px]' : 'font-medium text-xs'
                    }`}
                  >
                    {item.text}
                  </a>
                ))}
              </nav>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

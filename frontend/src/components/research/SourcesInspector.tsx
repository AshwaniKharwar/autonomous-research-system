import { useState, useMemo } from 'react';
import { ExternalLink, Globe, Search } from 'lucide-react';
import type { ResearchSessionResponse } from '../../api/types';
import {
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
} from '../ui/drawer';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { useUIStore } from '../../store/useUIStore';

interface SourceItem {
  taskKey: string;
  taskTitle: string;
  url: string;
  title: string;
  snippet?: string;
  domain: string;
}

interface SourcesInspectorProps {
  session: ResearchSessionResponse | null;
}

export function SourcesInspector({ session }: SourcesInspectorProps) {
  const { isSourcesDrawerOpen, setIsSourcesDrawerOpen } = useUIStore();
  const [filterQuery, setFilterQuery] = useState('');

  // Flatten sources from all tasks
  const allSources = useMemo(() => {
    if (!session?.tasks) return [];
    const list: SourceItem[] = [];

    for (const task of session.tasks) {
      if (Array.isArray(task.sources)) {
        for (const src of task.sources) {
          const rawUrl = src.url ? String(src.url) : '';
          let domain = 'unknown';
          try {
            if (rawUrl.startsWith('http')) {
              domain = new URL(rawUrl).hostname.replace(/^www\./, '');
            }
          } catch {
            domain = 'unknown';
          }

          list.push({
            taskKey: task.task_key,
            taskTitle: task.title,
            url: rawUrl,
            title: src.title ? String(src.title) : rawUrl || 'Untitled Source',
            snippet: src.snippet ? String(src.snippet) : undefined,
            domain,
          });
        }
      }
    }

    return list;
  }, [session?.tasks]);

  const filteredSources = useMemo(() => {
    if (!filterQuery.trim()) return allSources;
    const q = filterQuery.toLowerCase();
    return allSources.filter(
      (s) =>
        s.title.toLowerCase().includes(q) ||
        s.url.toLowerCase().includes(q) ||
        s.domain.toLowerCase().includes(q) ||
        s.taskKey.toLowerCase().includes(q) ||
        (s.snippet && s.snippet.toLowerCase().includes(q))
    );
  }, [allSources, filterQuery]);

  return (
    <Drawer open={isSourcesDrawerOpen} onOpenChange={setIsSourcesDrawerOpen}>
      <DrawerContent className="max-w-2xl sm:max-w-2xl">
        <DrawerHeader>
          <div className="flex items-center gap-2 text-emerald-500 font-medium text-xs">
            <Globe className="h-4 w-4" />
            <span>Research Grounding & Citations</span>
          </div>
          <DrawerTitle className="text-xl pt-1">
            Collected Web Sources ({allSources.length})
          </DrawerTitle>
          <DrawerDescription>
            All external citations, web pages, and documents retrieved by research agents
            during this session.
          </DrawerDescription>
        </DrawerHeader>

        <div className="pt-3 pb-1">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              placeholder="Filter by domain, title, keyword or task key..."
              className="pl-9 text-xs"
            />
          </div>
        </div>

        <DrawerBody className="space-y-3 pt-2">
          {filteredSources.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border p-8 text-center text-xs text-muted-foreground">
              {allSources.length === 0
                ? 'No external sources have been collected yet.'
                : 'No sources matched your filter query.'}
            </div>
          ) : (
            filteredSources.map((src, index) => (
              <div
                key={index}
                className="group rounded-xl border border-border/70 bg-card p-3.5 hover:border-primary/50 transition-colors text-xs space-y-2 shadow-xs"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <span className="font-semibold text-foreground text-sm line-clamp-1 group-hover:text-primary transition-colors">
                      {src.title}
                    </span>
                    <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                      <Badge variant="secondary" className="px-1.5 py-0 text-[10px]">
                        {src.domain}
                      </Badge>
                      <span>From {src.taskKey}</span>
                    </div>
                  </div>

                  {src.url && (
                    <a
                      href={src.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 rounded-md border border-border/80 bg-secondary/50 px-2.5 py-1 text-[11px] font-medium text-primary hover:bg-secondary transition-colors"
                    >
                      Visit
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>

                {src.snippet && (
                  <p className="text-muted-foreground line-clamp-3 bg-muted/30 rounded-md p-2 text-[11px]">
                    &quot;{src.snippet}&quot;
                  </p>
                )}
              </div>
            ))
          )}
        </DrawerBody>
      </DrawerContent>
    </Drawer>
  );
}

import { useState, useMemo } from 'react';
import {
  Compass,
  ListChecks,
  Moon,
  Plus,
  Search,
  Sun,
  Trash2,
  X,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { SessionItem } from './SessionItem';
import { DeleteConfirmDialog } from '../research/DeleteConfirmDialog';
import { BatchDeleteConfirmDialog } from '../research/BatchDeleteConfirmDialog';
import { useResearches } from '../../hooks/useResearches';
import { useUIStore } from '../../store/useUIStore';
import type { ResearchStatus } from '../../api/types';
import { Skeleton } from '../ui/skeleton';

const STATUS_FILTERS: Array<{ label: string; value: ResearchStatus | 'ALL' }> = [
  { label: 'All', value: 'ALL' },
  { label: 'Pending', value: 'PENDING_APPROVAL' },
  { label: 'Running', value: 'RUNNING' },
  { label: 'Done', value: 'COMPLETED' },
];

export function Sidebar() {
  const {
    activeSessionId,
    setActiveSessionId,
    statusFilter,
    setStatusFilter,
    setIsNewModalOpen,
  } = useUIStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [sessionToDelete, setSessionToDelete] = useState<{ id: string; query: string } | null>(null);
  const [isSelectMode, setIsSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isBatchDeleteDialogOpen, setIsBatchDeleteDialogOpen] = useState(false);
  const [isDark, setIsDark] = useState(true);

  const { data: sessions, isLoading, isError } = useResearches(statusFilter);

  const filteredSessions = useMemo(() => {
    if (!sessions) return [];
    if (!searchQuery.trim()) return sessions;
    const q = searchQuery.toLowerCase();
    return sessions.filter((s) => s.query.toLowerCase().includes(q));
  }, [sessions, searchQuery]);

  const selectedSessionsList = useMemo(() => {
    if (!sessions) return [];
    return sessions.filter((s) => selectedIds.has(s.id));
  }, [sessions, selectedIds]);

  const isAllSelected =
    filteredSessions.length > 0 &&
    filteredSessions.every((s) => selectedIds.has(s.id));
  const isSomeSelected =
    filteredSessions.some((s) => selectedIds.has(s.id)) && !isAllSelected;

  const toggleSelectAll = () => {
    if (isAllSelected) {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        for (const s of filteredSessions) {
          next.delete(s.id);
        }
        return next;
      });
    } else {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        for (const s of filteredSessions) {
          next.add(s.id);
        }
        return next;
      });
    }
  };

  const toggleSelectItem = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const exitSelectMode = () => {
    setIsSelectMode(false);
    setSelectedIds(new Set());
  };

  const toggleTheme = () => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.remove('dark');
      setIsDark(false);
    } else {
      root.classList.add('dark');
      setIsDark(true);
    }
  };

  return (
    <>
      <aside className="flex h-screen w-72 flex-col border-r border-border bg-card/60 backdrop-blur-xl">
        {/* Brand Header */}
        <div className="flex items-center justify-between p-4 pb-3 border-b border-border/60">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
              <Compass className="h-4 w-4" />
            </div>
            <div>
              <h1 className="text-sm font-semibold text-foreground tracking-tight">
                Deep Research
              </h1>
              <span className="text-[10px] text-muted-foreground block -mt-0.5">
                Multi-Agent System
              </span>
            </div>
          </div>

          <button
            onClick={toggleTheme}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
        </div>

        {/* New Research CTA */}
        <div className="p-3">
          <Button
            onClick={() => setIsNewModalOpen(true)}
            className="w-full justify-center gap-2 shadow-xs bg-primary hover:bg-primary/90 text-primary-foreground font-medium"
          >
            <Plus className="h-4 w-4" />
            New Research
          </Button>
        </div>

        {/* Search & Status Filters */}
        <div className="px-3 pb-2 space-y-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search history..."
              className="h-8 pl-8 text-xs"
            />
          </div>

          <div className="flex rounded-lg bg-secondary/50 p-0.5">
            {STATUS_FILTERS.map((f) => (
              <button
                key={f.value}
                onClick={() => setStatusFilter(f.value)}
                className={`flex-1 rounded-md py-1 text-[11px] font-medium transition-all ${
                  statusFilter === f.value
                    ? 'bg-card text-foreground shadow-xs'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Sessions List Header / Multi-Select Controls */}
        <div className="flex items-center justify-between px-3 pt-2 pb-1 text-xs">
          {isSelectMode ? (
            <div className="flex items-center justify-between w-full">
              <label className="flex items-center gap-2 cursor-pointer text-muted-foreground hover:text-foreground text-[11px]">
                <input
                  type="checkbox"
                  checked={isAllSelected}
                  ref={(el) => {
                    if (el) el.indeterminate = isSomeSelected;
                  }}
                  onChange={toggleSelectAll}
                  className="h-3.5 w-3.5 rounded border-border text-primary focus:ring-primary/20 cursor-pointer accent-primary"
                />
                <span>{isAllSelected ? 'Deselect All' : 'Select All'}</span>
              </label>
              <button
                type="button"
                onClick={exitSelectMode}
                className="text-[11px] text-muted-foreground hover:text-foreground flex items-center gap-1"
              >
                <X className="h-3 w-3" />
                Done
              </button>
            </div>
          ) : (
            <div className="flex items-center justify-between w-full text-muted-foreground">
              <span className="text-[11px] font-medium uppercase tracking-wider">
                Sessions {filteredSessions.length > 0 && `(${filteredSessions.length})`}
              </span>
              {filteredSessions.length > 0 && (
                <button
                  type="button"
                  onClick={() => setIsSelectMode(true)}
                  className="flex items-center gap-1 text-[11px] hover:text-foreground transition-colors p-1 rounded-md hover:bg-secondary/60"
                  title="Select multiple sessions"
                >
                  <ListChecks className="h-3.5 w-3.5" />
                  <span>Select</span>
                </button>
              )}
            </div>
          )}
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto px-3 py-1 space-y-1">
          {isLoading ? (
            <div className="space-y-2 pt-2">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full rounded-xl" />
              ))}
            </div>
          ) : isError ? (
            <div className="p-4 text-center text-xs text-destructive">
              Failed to load sessions. Ensure API backend is running.
            </div>
          ) : filteredSessions.length === 0 ? (
            <div className="p-6 text-center text-xs text-muted-foreground">
              {searchQuery ? 'No matching researches found.' : 'No research sessions yet.'}
            </div>
          ) : (
            filteredSessions.map((session) => (
              <SessionItem
                key={session.id}
                session={session}
                isActive={session.id === activeSessionId}
                isSelectMode={isSelectMode}
                isSelected={selectedIds.has(session.id)}
                onToggleSelect={() => toggleSelectItem(session.id)}
                onSelect={() => setActiveSessionId(session.id)}
                onDeleteClick={(e) => {
                  e.stopPropagation();
                  setSessionToDelete({ id: session.id, query: session.query });
                }}
              />
            ))
          )}
        </div>

        {/* Batch Delete Action Bar */}
        {isSelectMode && (
          <div className="p-3 border-t border-border/60 bg-card/80 backdrop-blur-sm space-y-2">
            <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
              <span>
                {selectedIds.size} of {filteredSessions.length} selected
              </span>
              <button
                type="button"
                onClick={exitSelectMode}
                className="text-[11px] hover:text-foreground underline underline-offset-2"
              >
                Cancel
              </button>
            </div>
            <Button
              variant="destructive"
              size="sm"
              disabled={selectedIds.size === 0}
              onClick={() => setIsBatchDeleteDialogOpen(true)}
              className="w-full gap-2 text-xs font-medium shadow-xs"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Delete Selected ({selectedIds.size})
            </Button>
          </div>
        )}
      </aside>

      <DeleteConfirmDialog
        sessionId={sessionToDelete?.id ?? null}
        queryPreview={sessionToDelete?.query}
        open={Boolean(sessionToDelete)}
        onOpenChange={(open) => {
          if (!open) setSessionToDelete(null);
        }}
      />

      <BatchDeleteConfirmDialog
        open={isBatchDeleteDialogOpen}
        onOpenChange={setIsBatchDeleteDialogOpen}
        selectedSessions={selectedSessionsList}
        onSuccess={() => {
          exitSelectMode();
        }}
      />
    </>
  );
}


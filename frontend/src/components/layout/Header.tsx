import {
  AlertOctagon,
  CheckCircle2,
  Cpu,
  FileText,
  ListTodo,
  Loader2,
  Menu,
  MoreVertical,
  RefreshCw,
  Sparkles,
  Trash2,
} from 'lucide-react';
import type { ResearchSessionResponse } from '../../api/types';
import { StatusBadge } from '../research/StatusBadge';
import { Button } from '../ui/button';
import { formatDate } from '../../utils/formatters';
import { useUIStore } from '../../store/useUIStore';
import { useResearchMutations } from '../../hooks/useResearchMutations';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';

interface HeaderProps {
  session: ResearchSessionResponse | null;
  onDeleteClick: () => void;
}

export function Header({ session, onDeleteClick }: HeaderProps) {
  const {
    activeTab,
    setActiveTab,
    sidebarOpen,
    setSidebarOpen,
    setIsReviseModalOpen,
  } = useUIStore();

  const { startMutation, cancelMutation } = useResearchMutations();

  if (!session) {
    return (
      <header className="flex h-14 items-center justify-between border-b border-border/80 px-6 bg-card/40 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSidebarOpen((prev) => !prev)}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
          >
            <Menu className="h-5 w-5" />
          </button>
          <span className="text-sm text-muted-foreground">Select a research session or start a new one</span>
        </div>
      </header>
    );
  }

  const isPending = session.status === 'PENDING_APPROVAL';
  const isRunning = session.status === 'RUNNING';
  const isCompleted = session.status === 'COMPLETED';

  return (
    <header className="flex flex-col border-b border-border/80 bg-card/40 backdrop-blur-md">
      {/* Top Bar: Title, Status, and Global Actions */}
      <div className="flex items-center justify-between gap-4 px-6 py-3.5">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={() => setSidebarOpen((prev) => !prev)}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors flex-shrink-0"
            title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="min-w-0">
            <div className="flex items-center gap-2.5">
              <h2 className="text-base font-semibold text-foreground truncate">
                {session.query}
              </h2>
              <StatusBadge status={session.status} className="flex-shrink-0" />
            </div>
            <span className="text-[11px] text-muted-foreground font-mono">
              Created {formatDate(session.created_at)}
            </span>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {isPending && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsReviseModalOpen(true)}
                className="gap-1.5 hidden sm:inline-flex"
              >
                <RefreshCw className="h-3.5 w-3.5 text-amber-500" />
                Revise Plan
              </Button>
              <Button
                size="sm"
                onClick={() => startMutation.mutate(session.id)}
                disabled={startMutation.isPending}
                className="gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white"
              >
                {startMutation.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <CheckCircle2 className="h-3.5 w-3.5" />
                )}
                Approve & Start
              </Button>
            </>
          )}

          {isRunning && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => cancelMutation.mutate(session.id)}
              disabled={cancelMutation.isPending}
              className="gap-1.5"
            >
              {cancelMutation.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <AlertOctagon className="h-3.5 w-3.5" />
              )}
              Cancel Research
            </Button>
          )}

          {/* More options menu */}
          <DropdownMenu.Root>
            <DropdownMenu.Trigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenu.Trigger>
            <DropdownMenu.Portal>
              <DropdownMenu.Content
                align="end"
                className="z-50 min-w-[160px] rounded-xl border border-border bg-popover p-1 text-popover-foreground shadow-xl animate-in fade-in-80"
              >
                {isPending && (
                  <DropdownMenu.Item
                    onClick={() => setIsReviseModalOpen(true)}
                    className="flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-foreground hover:bg-accent focus:bg-accent focus:outline-none sm:hidden"
                  >
                    <RefreshCw className="h-3.5 w-3.5 text-amber-500" />
                    Revise Plan
                  </DropdownMenu.Item>
                )}

                <DropdownMenu.Item
                  onClick={onDeleteClick}
                  className="flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-destructive hover:bg-destructive/10 focus:bg-destructive/10 focus:outline-none"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Delete Session
                </DropdownMenu.Item>
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>
        </div>
      </div>

      {/* Bottom Bar: Multi-view Navigation Tabs */}
      <div className="flex items-center gap-2 px-6 border-t border-border/40 overflow-x-auto">
        <NavTabButton
          active={activeTab === 'plan'}
          onClick={() => setActiveTab('plan')}
          icon={<ListTodo className="h-3.5 w-3.5" />}
          label="1. Plan & Subtasks"
          badge={session.tasks ? `${session.tasks.length}` : undefined}
        />
        <NavTabButton
          active={activeTab === 'pipeline'}
          onClick={() => setActiveTab('pipeline')}
          icon={<Cpu className="h-3.5 w-3.5" />}
          label="2. Wave Pipeline"
          isPulsing={isRunning}
        />
        <NavTabButton
          active={activeTab === 'report'}
          onClick={() => setActiveTab('report')}
          icon={
            isCompleted ? (
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
            ) : (
              <FileText className="h-3.5 w-3.5" />
            )
          }
          label="3. Research Report"
          highlight={isCompleted}
        />
      </div>
    </header>
  );
}

function NavTabButton({
  active,
  onClick,
  icon,
  label,
  badge,
  isPulsing,
  highlight,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  badge?: string;
  isPulsing?: boolean;
  highlight?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`group flex items-center gap-2 border-b-2 py-3 px-3 text-xs font-medium transition-all ${
        active
          ? 'border-primary text-primary'
          : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
      }`}
    >
      <span className={isPulsing ? 'animate-pulse text-sky-500' : ''}>{icon}</span>
      <span>{label}</span>
      {badge && (
        <span
          className={`rounded-full px-1.5 py-0.2 text-[10px] font-mono ${
            active
              ? 'bg-primary/10 text-primary'
              : 'bg-secondary text-muted-foreground group-hover:text-foreground'
          }`}
        >
          {badge}
        </span>
      )}
      {highlight && !active && (
        <Sparkles className="h-3 w-3 text-emerald-500" />
      )}
    </button>
  );
}

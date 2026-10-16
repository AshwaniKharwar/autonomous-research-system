import { create } from 'zustand';
import type { ResearchStatus } from '../api/types';

export type WorkspaceTab = 'plan' | 'pipeline' | 'report';

interface UIState {
  activeSessionId: string | null;
  activeTab: WorkspaceTab;
  sidebarOpen: boolean;
  statusFilter: ResearchStatus | 'ALL';
  isNewModalOpen: boolean;
  isReviseModalOpen: boolean;
  selectedTaskId: string | null; // task_key or id
  isSourcesDrawerOpen: boolean;

  setActiveSessionId: (id: string | null) => void;
  setActiveTab: (tab: WorkspaceTab) => void;
  setSidebarOpen: (open: boolean | ((prev: boolean) => boolean)) => void;
  setStatusFilter: (filter: ResearchStatus | 'ALL') => void;
  setIsNewModalOpen: (open: boolean) => void;
  setIsReviseModalOpen: (open: boolean) => void;
  setSelectedTaskId: (taskId: string | null) => void;
  setIsSourcesDrawerOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  activeSessionId: null,
  activeTab: 'plan',
  sidebarOpen: true,
  statusFilter: 'ALL',
  isNewModalOpen: false,
  isReviseModalOpen: false,
  selectedTaskId: null,
  isSourcesDrawerOpen: false,

  setActiveSessionId: (id) =>
    set({
      activeSessionId: id,
      selectedTaskId: null,
      isSourcesDrawerOpen: false,
    }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setSidebarOpen: (open) =>
    set((state) => ({
      sidebarOpen: typeof open === 'function' ? open(state.sidebarOpen) : open,
    })),
  setStatusFilter: (statusFilter) => set({ statusFilter }),
  setIsNewModalOpen: (isNewModalOpen) => set({ isNewModalOpen }),
  setIsReviseModalOpen: (isReviseModalOpen) => set({ isReviseModalOpen }),
  setSelectedTaskId: (selectedTaskId) => set({ selectedTaskId }),
  setIsSourcesDrawerOpen: (isSourcesDrawerOpen) => set({ isSourcesDrawerOpen }),
}));

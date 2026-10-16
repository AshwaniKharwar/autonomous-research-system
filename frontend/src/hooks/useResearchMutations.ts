import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  cancelResearch,
  createResearch,
  deleteResearch,
  reviseResearch,
  startResearch,
} from '../api/researches';
import type {
  ResearchCreateRequest,
  ResearchReviseRequest,
} from '../api/types';
import { RESEARCHES_QUERY_KEY } from './useResearches';
import { RESEARCH_SESSION_QUERY_KEY } from './useResearchSession';
import { useUIStore } from '../store/useUIStore';

export function useResearchMutations() {
  const queryClient = useQueryClient();
  const { setActiveSessionId, setIsNewModalOpen, setIsReviseModalOpen, setActiveTab } =
    useUIStore();

  const createMutation = useMutation({
    mutationFn: (data: ResearchCreateRequest) => createResearch(data),
    onSuccess: (newSession) => {
      queryClient.invalidateQueries({ queryKey: RESEARCHES_QUERY_KEY });
      queryClient.setQueryData([RESEARCH_SESSION_QUERY_KEY, newSession.id], newSession);
      setActiveSessionId(newSession.id);
      setActiveTab('plan');
      setIsNewModalOpen(false);
    },
  });

  const reviseMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: ResearchReviseRequest }) =>
      reviseResearch(id, data),
    onSuccess: (updatedSession) => {
      queryClient.invalidateQueries({ queryKey: RESEARCHES_QUERY_KEY });
      queryClient.setQueryData(
        [RESEARCH_SESSION_QUERY_KEY, updatedSession.id],
        updatedSession
      );
      setIsReviseModalOpen(false);
    },
  });

  const startMutation = useMutation({
    mutationFn: (id: string) => startResearch(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: RESEARCHES_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: [RESEARCH_SESSION_QUERY_KEY, id] });
      setActiveTab('pipeline');
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => cancelResearch(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: RESEARCHES_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: [RESEARCH_SESSION_QUERY_KEY, id] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteResearch(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: RESEARCHES_QUERY_KEY });
      queryClient.removeQueries({ queryKey: [RESEARCH_SESSION_QUERY_KEY, id] });
      const currentActiveId = useUIStore.getState().activeSessionId;
      if (currentActiveId === id) {
        setActiveSessionId(null);
      }
    },
  });

  return {
    createMutation,
    reviseMutation,
    startMutation,
    cancelMutation,
    deleteMutation,
  };
}

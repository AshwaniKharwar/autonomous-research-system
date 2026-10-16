import { useQuery } from '@tanstack/react-query';
import { getResearch } from '../api/researches';
import type { ResearchSessionResponse } from '../api/types';

export const RESEARCH_SESSION_QUERY_KEY = 'research_session';

export function useResearchSession(id: string | null) {
  return useQuery<ResearchSessionResponse | null>({
    queryKey: [RESEARCH_SESSION_QUERY_KEY, id],
    queryFn: () => (id ? getResearch(id) : null),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data && data.status === 'RUNNING') {
        return 2000;
      }
      return false;
    },
    refetchIntervalInBackground: false,
    staleTime: 1000,
  });
}

import { useQuery } from '@tanstack/react-query';
import { listResearches } from '../api/researches';
import type { ResearchStatus } from '../api/types';

export const RESEARCHES_QUERY_KEY = ['researches'];

export function useResearches(status?: ResearchStatus | 'ALL') {
  const statusParam = status && status !== 'ALL' ? status : undefined;

  return useQuery({
    queryKey: [...RESEARCHES_QUERY_KEY, statusParam],
    queryFn: () => listResearches({ status: statusParam }),
    staleTime: 5000,
  });
}

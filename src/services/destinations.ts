import { z } from 'zod';

import { apiRequest } from '@/services/api';
import type { Coordinate, Destination } from '@/types/smartpark';

const coordinateSchema = z.object({
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
});

const destinationSchema: z.ZodType<Destination> = z.object({
  id: z.string(),
  name: z.string(),
  category: z.string().nullable(),
  address: z.string().nullable(),
  location: coordinateSchema,
});

const destinationSearchResponseSchema = z.object({
  results: z.array(destinationSchema),
});

export type DestinationSearchOptions = {
  limit?: number;
  bias?: Coordinate;
  signal?: AbortSignal;
};

export async function searchDestinations(
  query: string,
  options: DestinationSearchOptions = {},
): Promise<Destination[]> {
  const parameters = new URLSearchParams({
    q: query,
    limit: String(options.limit ?? 5),
  });
  if (options.bias) {
    parameters.set('latitude', String(options.bias.latitude));
    parameters.set('longitude', String(options.bias.longitude));
  }

  const response = await apiRequest(
    `/api/destinations/search?${parameters.toString()}`,
    destinationSearchResponseSchema,
    { signal: options.signal },
  );
  return response.results;
}

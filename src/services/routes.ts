import { z } from 'zod';

import { apiRequest } from '@/services/api';
import type {
  Coordinate,
  RouteResult,
  VehicleType,
} from '@/types/smartpark';

const routeResponseSchema: z.ZodType<RouteResult> = z.object({
  geometry: z.object({
    type: z.literal('LineString'),
    coordinates: z.array(z.tuple([z.number(), z.number()])).min(2),
  }),
  distanceMeters: z.number().finite().nonnegative(),
  durationSeconds: z.number().finite().nonnegative(),
});

export async function getRoute(
  mode: VehicleType | 'walk',
  origin: Coordinate,
  destination: Coordinate,
  signal?: AbortSignal,
): Promise<RouteResult> {
  return apiRequest(
    `/api/routes/${mode}`,
    routeResponseSchema,
    {
      method: 'POST',
      body: JSON.stringify({ origin, destination }),
      signal,
    },
  );
}

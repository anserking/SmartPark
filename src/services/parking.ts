import { z } from 'zod';

import { apiRequest } from '@/services/api';
import type { Coordinate, MapParkingFacility } from '@/types/smartpark';

const parkingFacilitySchema: z.ZodType<MapParkingFacility> = z.object({
  id: z.string(),
  name: z.string().nullable(),
  address: z.string().nullable(),
  location: z.object({
    latitude: z.number().min(-90).max(90),
    longitude: z.number().min(-180).max(180),
  }),
  parkingType: z.string(),
  fee: z.string().nullable(),
  capacity: z.number().int().nonnegative().nullable(),
  supportsCar: z.boolean().nullable(),
  supportsBike: z.boolean().nullable(),
  straightLineDistanceMeters: z.number().nonnegative(),
  availabilityStatus: z.literal('unknown'),
  verificationStatus: z.literal('unverified'),
  source: z.literal('openstreetmap'),
});

const parkingSearchResponseSchema = z.object({
  results: z.array(parkingFacilitySchema),
});

export async function searchParkingFacilities(
  center: Coordinate,
  radiusMeters = 1500,
  limit = 10,
  signal?: AbortSignal,
): Promise<MapParkingFacility[]> {
  const parameters = new URLSearchParams({
    latitude: String(center.latitude),
    longitude: String(center.longitude),
    radius_meters: String(radiusMeters),
    limit: String(limit),
  });
  const response = await apiRequest(
    `/api/parking/search?${parameters.toString()}`,
    parkingSearchResponseSchema,
    { signal },
  );
  return response.results;
}

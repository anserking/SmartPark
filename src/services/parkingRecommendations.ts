import { z } from 'zod';

import { apiRequest } from '@/services/api';
import type {
  Coordinate,
  ParkingRecommendation,
  VehicleType,
} from '@/types/smartpark';

const parkingRecommendationSchema: z.ZodType<ParkingRecommendation> = z.object({
  id: z.string(),
  name: z.string().nullable(),
  address: z.string().nullable(),
  location: z.object({
    latitude: z.number().min(-90).max(90),
    longitude: z.number().min(-180).max(180),
  }),
  parkingType: z.string(),
  fee: z.string().nullable(),
  hourlyFee: z.number().nonnegative().nullable(),
  capacity: z.number().int().nonnegative().nullable(),
  supportsCar: z.boolean().nullable(),
  supportsBike: z.boolean().nullable(),
  destinationDistanceMeters: z.number().nonnegative(),
  destinationDistanceMethod: z.enum(['road', 'straight_line']),
  userDistanceMeters: z.number().nonnegative().nullable(),
  availabilityStatus: z.enum([
    'verified',
    'unverified',
    'unavailable',
    'unknown',
  ]),
  verificationStatus: z.enum(['verified', 'unverified']),
  source: z.string(),
});

const responseSchema = z.object({
  results: z.array(parkingRecommendationSchema),
  distanceMethod: z.enum(['road', 'straight_line']),
});

export async function getParkingRecommendations(
  destination: Coordinate,
  destinationName: string,
  vehicleType: VehicleType,
  userLocation?: Coordinate | null,
  signal?: AbortSignal,
): Promise<ParkingRecommendation[]> {
  const parameters = new URLSearchParams({
    latitude: String(destination.latitude),
    longitude: String(destination.longitude),
    vehicle_type: vehicleType,
    radius_meters: '2000',
    limit: '5',
    destination_name: destinationName,
  });
  if (userLocation) {
    parameters.set('user_latitude', String(userLocation.latitude));
    parameters.set('user_longitude', String(userLocation.longitude));
  }

  const response = await apiRequest(
    `/api/parking/recommendations?${parameters.toString()}`,
    responseSchema,
    { signal },
  );
  return response.results;
}

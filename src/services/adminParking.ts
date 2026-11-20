import { z } from 'zod';

import { apiRequest } from '@/services/api';
import type { AdminParkingSpot } from '@/types/smartpark';

const parkingSpotSchema: z.ZodType<AdminParkingSpot> = z.object({
  id: z.string().uuid(),
  name: z.string().nullable(),
  address: z.string().nullable(),
  location: z.object({
    latitude: z.number().min(-90).max(90),
    longitude: z.number().min(-180).max(180),
  }),
  parkingType: z.string().nullable(),
  hourlyFee: z.number().nonnegative().nullable(),
  supportsCar: z.boolean().nullable(),
  supportsBike: z.boolean().nullable(),
  capacity: z.number().int().nonnegative().nullable(),
  availableSpaces: z.number().int().nonnegative().nullable(),
  availabilityStatus: z.enum(['verified', 'unverified', 'unavailable', 'unknown']),
  verificationStatus: z.enum(['verified', 'unverified']),
  source: z.string(),
});

const deleteResponseSchema = z.object({ deleted: z.literal(true) });

export type AdminParkingSpotInput = Omit<AdminParkingSpot, 'id' | 'source'>;
export type AdminParkingSpotPatch = Partial<AdminParkingSpotInput>;

const request = <T>(
  path: string,
  adminKey: string,
  schema: z.ZodType<T>,
  init?: RequestInit,
) =>
  apiRequest(path, schema, {
    ...init,
    headers: {
      ...init?.headers,
      Authorization: `Bearer ${adminKey}`,
    },
  });

export const listAdminParkingSpots = (adminKey: string) =>
  request('/api/admin/parking', adminKey, z.array(parkingSpotSchema));

export const createAdminParkingSpot = (
  adminKey: string,
  spot: AdminParkingSpotInput,
) =>
  request('/api/admin/parking', adminKey, parkingSpotSchema, {
    method: 'POST',
    body: JSON.stringify(spot),
  });

export const updateAdminParkingSpot = (
  adminKey: string,
  spotId: string,
  changes: AdminParkingSpotPatch,
) =>
  request(
    `/api/admin/parking/${encodeURIComponent(spotId)}`,
    adminKey,
    parkingSpotSchema,
    {
      method: 'PATCH',
      body: JSON.stringify(changes),
    },
  );

export const deleteAdminParkingSpot = (adminKey: string, spotId: string) =>
  request(
    `/api/admin/parking/${encodeURIComponent(spotId)}`,
    adminKey,
    deleteResponseSchema,
    { method: 'DELETE' },
  );

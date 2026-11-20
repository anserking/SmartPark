import { afterEach, describe, expect, it, vi } from 'vitest';

import { searchParkingFacilities } from './parking';

describe('Google parking API client', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('requests nearby mapped facilities and validates the response', async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(
          JSON.stringify({
            results: [
              {
                id: 'way/parking-1',
                name: 'Clifton lot',
                address: 'Clifton, Karachi',
                location: { latitude: 24.855, longitude: 67.021 },
                parkingType: 'parking',
                fee: 'yes',
                capacity: 30,
                supportsCar: true,
                supportsBike: null,
                straightLineDistanceMeters: 100,
                availabilityStatus: 'unknown',
                verificationStatus: 'unverified',
                source: 'google_maps',
              },
            ],
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
    );
    vi.stubGlobal('fetch', fetchMock);

    const results = await searchParkingFacilities(
      { latitude: 24.8546842, longitude: 67.0207055 },
      1200,
      5,
    );

    expect(results).toHaveLength(1);
    expect(results[0].id).toBe('way/parking-1');
    const [url] = fetchMock.mock.calls[0];
    expect(new URL(String(url)).origin).toBe('http://localhost:5173');
    expect(new URL(String(url)).pathname).toBe('/api/parking/search');
    expect(new URL(String(url)).searchParams.get('radius_meters')).toBe('1200');
    expect(new URL(String(url)).searchParams.get('limit')).toBe('5');
  });
});

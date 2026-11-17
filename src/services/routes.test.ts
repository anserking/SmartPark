import { afterEach, describe, expect, it, vi } from 'vitest';

import { getRoute } from './routes';

describe('route API client', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('requests a route and validates the normalized result', async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(
          JSON.stringify({
            geometry: {
              type: 'LineString',
              coordinates: [
                [67.03, 24.86],
                [67.031, 24.861],
              ],
            },
            distanceMeters: 100,
            durationSeconds: 120,
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(
      getRoute(
        'car',
        { latitude: 24.86, longitude: 67.03 },
        { latitude: 24.861, longitude: 67.031 },
      ),
    ).resolves.toEqual({
      geometry: {
        type: 'LineString',
        coordinates: [
          [67.03, 24.86],
          [67.031, 24.861],
        ],
      },
      distanceMeters: 100,
      durationSeconds: 120,
    });

    const [url, init] = fetchMock.mock.calls[0];
    expect(new URL(String(url)).pathname).toBe('/api/routes/car');
    expect(JSON.parse(String(init?.body))).toEqual({
      origin: { latitude: 24.86, longitude: 67.03 },
      destination: { latitude: 24.861, longitude: 67.031 },
    });
  });

  it('rejects malformed route geometry', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            geometry: { type: 'LineString', coordinates: [[67.03, 24.86]] },
            distanceMeters: 100,
            durationSeconds: 120,
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } },
        ),
      ),
    );

    await expect(
      getRoute(
        'walk',
        { latitude: 24.86, longitude: 67.03 },
        { latitude: 24.861, longitude: 67.031 },
      ),
    ).rejects.toThrow();
  });
});

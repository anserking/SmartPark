import { afterEach, describe, expect, it, vi } from 'vitest';

import { getParkingRecommendations } from './parkingRecommendations';

afterEach(() => vi.unstubAllGlobals());

describe('parking recommendations request', () => {
  it('uses the selected destination and starting location', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ results: [], distanceMethod: 'straight_line' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await getParkingRecommendations(
      { latitude: 24.893277, longitude: 67.0881814 },
      'Bahria University Karachi',
      'car',
      { latitude: 24.8299, longitude: 67.16 },
    );

    const request = new URL(String(fetchMock.mock.calls[0][0]));
    expect(request.pathname).toBe('/api/parking/recommendations');
    expect(request.searchParams.get('destination_name')).toBe('Bahria University Karachi');
    expect(request.searchParams.get('latitude')).toBe('24.893277');
    expect(request.searchParams.get('longitude')).toBe('67.0881814');
    expect(request.searchParams.get('user_latitude')).toBe('24.8299');
    expect(request.searchParams.get('user_longitude')).toBe('67.16');
  });
});

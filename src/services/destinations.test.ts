import { afterEach, describe, expect, it, vi } from 'vitest';

import { searchDestinations } from '@/services/destinations';

const destination = {
  id: '550e8400-e29b-41d4-a716-446655440000',
  name: 'Bahria University Karachi',
  category: 'university',
  address: 'Karachi',
  location: { latitude: 24.86, longitude: 67.03 },
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('destination service', () => {
  it('sends search text and optional location bias to the API', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ results: [destination] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(
      searchDestinations('Bahria & University', {
        bias: { latitude: 24.9, longitude: 67.1 },
      }),
    ).resolves.toEqual([destination]);

    const requestUrl = new URL(String(fetchMock.mock.calls[0][0]));
    expect(requestUrl.pathname).toBe('/api/destinations/search');
    expect(requestUrl.searchParams.get('q')).toBe('Bahria & University');
    expect(requestUrl.searchParams.get('limit')).toBe('5');
    expect(requestUrl.searchParams.get('latitude')).toBe('24.9');
    expect(requestUrl.searchParams.get('longitude')).toBe('67.1');
  });

  it('rejects malformed destination coordinates from the API', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          results: [
            {
              ...destination,
              location: { latitude: 24.86, longitude: 181 },
            },
          ],
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(searchDestinations('Bahria University')).rejects.toThrow();
  });
});

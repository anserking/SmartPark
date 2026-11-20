import { z } from 'zod';

const browserOrigin =
  typeof window === 'undefined' ? 'http://localhost:5173' : window.location.origin;
const apiBaseUrl = import.meta.env.DEV
  ? browserOrigin
  : (import.meta.env.VITE_API_BASE_URL || browserOrigin).replace(/\/+$/, '');

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

function getErrorMessage(payload: unknown, status: number): string {
  if (
    typeof payload === 'object' &&
    payload !== null &&
    'detail' in payload &&
    typeof payload.detail === 'string'
  ) {
    return payload.detail;
  }
  return `API request failed (${status})`;
}

export async function apiRequest<T>(
  path: string,
  schema: z.ZodType<T>,
  init?: RequestInit,
): Promise<T> {
  const url = new URL(path.replace(/^\/+/, ''), `${apiBaseUrl}/`);
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, { ...init, headers });
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new ApiError(
      `API returned invalid JSON (${response.status})`,
      response.status,
    );
  }

  if (!response.ok) {
    throw new ApiError(getErrorMessage(payload, response.status), response.status);
  }

  return schema.parse(payload);
}

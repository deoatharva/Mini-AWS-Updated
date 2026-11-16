import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  ApiError,
  api,
  getErrorMessage,
  getStoredToken,
  setUnauthorizedHandler,
  storeToken,
} from './api.js';

const fetchMock = vi.fn();

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async () => body,
  };
}

function emptyResponse(status = 204) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers(),
    json: async () => null,
  };
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  window.localStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
  setUnauthorizedHandler(null);
});

describe('api client', () => {
  it('registers without an Authorization header and stores no token itself', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ access_token: 'token-1', user: { id: 1 } }, 201),
    );

    const result = await api.auth.register({
      name: 'Jane',
      email: 'jane@example.com',
      password: 'correct-horse-battery',
    });

    expect(result.access_token).toBe('token-1');
    expect(getStoredToken()).toBeNull();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/auth\/register$/);
    expect(options.method).toBe('POST');
    expect(options.headers.Authorization).toBeUndefined();
    expect(JSON.parse(options.body)).toEqual({
      name: 'Jane',
      email: 'jane@example.com',
      password: 'correct-horse-battery',
    });
  });

  it('sends the stored bearer token for authenticated requests', async () => {
    storeToken('saved-token');
    fetchMock.mockResolvedValue(jsonResponse({ id: 1, name: 'Jane' }));

    await api.auth.me();

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers.Authorization).toBe('Bearer saved-token');
  });

  it('notifies the auth provider when an authenticated request returns 401', async () => {
    storeToken('expired-token');
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          error: {
            code: 'session_expired',
            message: 'Your session has expired. Sign in again.',
          },
        },
        401,
      ),
    );

    await expect(api.auth.me()).rejects.toMatchObject({
      code: 'session_expired',
      status: 401,
    });
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it('does not treat a failed unauthenticated login as a lost session', async () => {
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          error: {
            code: 'invalid_credentials',
            message: 'Email or password is incorrect.',
          },
        },
        401,
      ),
    );

    await expect(
      api.auth.login({ email: 'jane@example.com', password: 'wrong' }),
    ).rejects.toMatchObject({ code: 'invalid_credentials' });
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it('returns null for 204 responses', async () => {
    storeToken('saved-token');
    fetchMock.mockResolvedValue(emptyResponse(204));

    await expect(api.auth.logout()).resolves.toBeNull();
  });

  it('reports an actionable message when the API is unreachable', async () => {
    fetchMock.mockRejectedValue(new TypeError('fetch failed'));

    await expect(api.health()).rejects.toThrow(/Cannot reach the local API/);
  });

  it('formats backend validation details for display', () => {
    const error = new ApiError('Request validation failed.', {
      status: 422,
      code: 'validation_error',
      details: [
        {
          field: 'password',
          message: 'String should have at least 12 characters.',
        },
      ],
    });

    expect(getErrorMessage(error)).toBe(
      'Password: String should have at least 12 characters.',
    );
  });
});

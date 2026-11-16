import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AppRoutes } from '../routes/AppRoutes.jsx';
import { getStoredToken, storeToken } from '../services/api.js';

const fetchMock = vi.fn();

const localUser = {
  id: 7,
  name: 'Jane Doe',
  email: 'jane@example.com',
  created_at: '2026-11-16T10:00:00Z',
};

const session = {
  access_token: 'test-token',
  token_type: 'bearer',
  expires_at: '2026-11-17T10:00:00Z',
  user: localUser,
};

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
  window.history.pushState({}, '', '/');
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('account workflow', () => {
  it('redirects anonymous visitors from the console to sign in', async () => {
    render(<AppRoutes />);

    expect(
      await screen.findByRole('heading', { name: 'Sign in' }),
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe('/login');
  });

  it('creates a local account and opens the console', async () => {
    window.history.pushState({}, '', '/register');
    fetchMock.mockResolvedValueOnce(jsonResponse(session, 201));
    const user = userEvent.setup();

    render(<AppRoutes />);

    await user.type(await screen.findByLabelText('Name'), 'Jane Doe');
    await user.type(screen.getByLabelText('Email'), 'jane@example.com');
    await user.type(
      screen.getByLabelText('Password'),
      'correct-horse-battery',
    );
    await user.type(
      screen.getByLabelText('Confirm password'),
      'correct-horse-battery',
    );
    await user.click(screen.getByRole('button', { name: 'Create account' }));

    expect(
      await screen.findByRole('heading', {
        name: 'Welcome back, Jane Doe',
      }),
    ).toBeInTheDocument();
    expect(getStoredToken()).toBe('test-token');

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/auth\/register$/);
    expect(JSON.parse(options.body)).toEqual({
      name: 'Jane Doe',
      email: 'jane@example.com',
      password: 'correct-horse-battery',
    });
  });

  it('shows a useful error for invalid credentials', async () => {
    window.history.pushState({}, '', '/login');
    fetchMock.mockResolvedValueOnce(
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
    const user = userEvent.setup();

    render(<AppRoutes />);

    await user.type(await screen.findByLabelText('Email'), 'jane@example.com');
    await user.type(screen.getByLabelText('Password'), 'wrong-password');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Email or password is incorrect.',
    );
    expect(window.location.pathname).toBe('/login');
    expect(getStoredToken()).toBeNull();
  });

  it('signs in and opens the console', async () => {
    window.history.pushState({}, '', '/login');
    fetchMock.mockResolvedValueOnce(jsonResponse(session));
    const user = userEvent.setup();

    render(<AppRoutes />);

    await user.type(await screen.findByLabelText('Email'), 'jane@example.com');
    await user.type(screen.getByLabelText('Password'), 'correct-horse-battery');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(
      await screen.findByRole('heading', {
        name: 'Welcome back, Jane Doe',
      }),
    ).toBeInTheDocument();
    expect(getStoredToken()).toBe('test-token');
  });

  it('returns to the requested console page after signing in', async () => {
    window.history.pushState({}, '', '/account');
    fetchMock.mockResolvedValueOnce(jsonResponse(session));
    const user = userEvent.setup();

    render(<AppRoutes />);

    await user.type(await screen.findByLabelText('Email'), 'jane@example.com');
    await user.type(screen.getByLabelText('Password'), 'correct-horse-battery');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(
      await screen.findByRole('heading', { name: 'Account settings' }),
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe('/account');
  });

  it('restores a stored session, shows the account, and signs out', async () => {
    window.history.pushState({}, '', '/account');
    storeToken('test-token');
    fetchMock
      .mockResolvedValueOnce(jsonResponse(localUser))
      .mockResolvedValueOnce(emptyResponse(204));
    const user = userEvent.setup();

    render(<AppRoutes />);

    expect(
      await screen.findByRole('heading', { name: 'Account settings' }),
    ).toBeInTheDocument();
    expect(screen.getByText('jane@example.com')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Sign out' }));

    expect(
      await screen.findByRole('heading', { name: 'Sign in' }),
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe('/login');
    expect(getStoredToken()).toBeNull();
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining('/auth/logout'),
      expect.objectContaining({ method: 'POST' }),
    );
  });
});

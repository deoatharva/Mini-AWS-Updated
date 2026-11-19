import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { getStoredToken, storeToken } from '../services/api.js';
import { AppRoutes } from './AppRoutes.jsx';

const fetchMock = vi.fn();

const account = {
  id: 12,
  account_id: '123456789012',
  name: 'Lab Account',
  status: 'active',
  created_at: '2026-11-16T09:00:00Z',
};

const iamUser = {
  id: 8,
  account_id: 12,
  username: 'student1',
  name: 'Student One',
  display_name: 'Student One',
  email: null,
  user_type: 'IAM',
  status: 'active',
  console_access_enabled: true,
  must_change_password: false,
  created_at: '2026-11-16T10:00:00Z',
  updated_at: '2026-11-16T10:00:00Z',
  last_login_at: null,
  account,
  groups: [{ id: 3, name: 'ReadOnlyTeam' }],
  permissions: ['dashboard:Read', 'compute:ListInstances'],
};

const dashboardSummary = {
  counts: {
    compute_total: 0,
    compute_running: 0,
    applications_total: 0,
    applications_running: 0,
    buckets_total: 0,
    objects_total: 0,
    storage_bytes: 0,
    databases_total: 0,
  },
  recent_activity: [],
};

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async () => body,
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

describe('IAM authentication workflows', () => {
  it('signs in with account ID and username, then shows IAM identity in the console', async () => {
    window.history.pushState({}, '', '/login/iam');
    fetchMock.mockImplementation(async (url, options = {}) => {
      if (url.endsWith('/auth/iam/login') && options.method === 'POST') {
        return jsonResponse({
          access_token: 'iam-token',
          token_type: 'bearer',
          expires_at: '2026-11-20T10:00:00Z',
          user: iamUser,
        });
      }
      if (url.endsWith('/dashboard')) {
        return jsonResponse(dashboardSummary);
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    const user = userEvent.setup();

    render(<AppRoutes />);

    await user.type(
      await screen.findByLabelText('Local Account ID'),
      '123456789012',
    );
    await user.type(screen.getByLabelText('IAM username'), 'Student1');
    await user.type(screen.getByLabelText('Password'), 'temporary-pass-123');
    await user.click(
      screen.getByRole('button', { name: 'Sign in as IAM user' }),
    );

    expect(
      await screen.findByRole('heading', {
        name: 'Welcome back, Student One',
      }),
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe('/');
    expect(getStoredToken()).toBe('iam-token');
    expect(screen.getByText(/Account 123456789012/)).toBeInTheDocument();
    expect(screen.getByText(/IAM user/)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'IAM Users' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Audit Log' })).not.toBeInTheDocument();

    const loginCall = fetchMock.mock.calls.find(([url]) =>
      url.endsWith('/auth/iam/login'),
    );
    expect(JSON.parse(loginCall[1].body)).toEqual({
      account_id: '123456789012',
      username: 'student1',
      password: 'temporary-pass-123',
    });
  });

  it('redirects a temporary-password IAM session to the mandatory change page and then opens the console', async () => {
    window.history.pushState({}, '', '/iam/users');
    storeToken('temporary-token');
    const pendingUser = { ...iamUser, must_change_password: true };
    const readyUser = { ...iamUser, must_change_password: false };
    fetchMock.mockImplementation(async (url, options = {}) => {
      if (url.endsWith('/auth/me')) {
        return jsonResponse(pendingUser);
      }
      if (url.endsWith('/auth/change-password') && options.method === 'POST') {
        return jsonResponse(readyUser);
      }
      if (url.endsWith('/dashboard')) {
        return jsonResponse(dashboardSummary);
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    const user = userEvent.setup();

    render(<AppRoutes />);

    expect(
      await screen.findByRole('heading', { name: 'Change temporary password' }),
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe('/account/change-password');
    expect(
      fetchMock.mock.calls.some(([url]) => url.endsWith('/iam/users')),
    ).toBe(false);

    await user.type(
      screen.getByLabelText('New password'),
      'replacement-pass-789',
    );
    await user.type(
      screen.getByLabelText('Confirm new password'),
      'replacement-pass-789',
    );
    await user.click(screen.getByRole('button', { name: 'Set new password' }));

    expect(
      await screen.findByRole('heading', {
        name: 'Welcome back, Student One',
      }),
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe('/');
    const changeCall = fetchMock.mock.calls.find(([url]) =>
      url.endsWith('/auth/change-password'),
    );
    expect(JSON.parse(changeCall[1].body)).toEqual({
      new_password: 'replacement-pass-789',
      confirm_password: 'replacement-pass-789',
    });
  });

  it('hides unauthorized IAM navigation and shows an access-denied page for a direct route', async () => {
    window.history.pushState({}, '', '/iam/users/new');
    storeToken('readonly-token');
    const readOnlyUser = {
      ...iamUser,
      permissions: [
        'dashboard:Read',
        'iam:ReadOverview',
        'iam:ListUsers',
        'iam:GetUser',
      ],
    };
    fetchMock.mockImplementation(async (url) => {
      if (url.endsWith('/auth/me')) {
        return jsonResponse(readOnlyUser);
      }
      throw new Error(`Unexpected request: ${url}`);
    });

    render(<AppRoutes />);

    expect(
      await screen.findByRole('heading', { name: 'Access denied' }),
    ).toBeInTheDocument();
    expect(screen.getByText('iam:CreateUser')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'IAM Users' })).toBeInTheDocument();
    expect(
      screen.queryByRole('link', { name: 'IAM Policies' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('link', { name: 'Audit Log' }),
    ).not.toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(([url]) => url.endsWith('/iam/users')),
    ).toBe(false);
  });
});

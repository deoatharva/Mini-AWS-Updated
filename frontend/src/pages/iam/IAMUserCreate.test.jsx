import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AppRoutes } from '../../routes/AppRoutes.jsx';
import { storeToken } from '../../services/api.js';

const fetchMock = vi.fn();

const account = {
  id: 12,
  account_id: '123456789012',
  name: 'Lab Account',
  status: 'active',
  created_at: '2026-11-16T09:00:00Z',
};

const owner = {
  id: 1,
  account_id: 12,
  username: 'owner',
  name: 'Account Owner',
  display_name: 'Account Owner',
  email: 'owner@example.com',
  user_type: 'OWNER',
  status: 'active',
  console_access_enabled: true,
  must_change_password: false,
  created_at: '2026-11-16T09:00:00Z',
  updated_at: '2026-11-16T09:00:00Z',
  last_login_at: null,
  account,
  groups: [],
  permissions: [],
};

const group = {
  id: 3,
  name: 'LabOperators',
  description: 'Operate the compute lab.',
  user_count: 0,
  policy_count: 1,
  created_at: '2026-11-16T10:00:00Z',
  updated_at: '2026-11-16T10:00:00Z',
};

const createdUser = {
  id: 42,
  account_id: '123456789012',
  username: 'student2',
  display_name: 'Student Two',
  status: 'active',
  console_access_enabled: true,
  must_change_password: true,
  groups: [{ id: 3, name: 'LabOperators' }],
  created_at: '2026-11-16T11:00:00Z',
  updated_at: '2026-11-16T11:00:00Z',
  last_login_at: null,
  effective_actions: ['dashboard:Read', 'compute:ListInstances'],
  permission_sources: {
    'dashboard:Read': [
      {
        type: 'group',
        name: 'LabOperators',
        policy_id: 2,
        policy_name: 'ReadOnlyAccess',
        group_id: 3,
        group_name: 'LabOperators',
      },
    ],
    'compute:ListInstances': [
      {
        type: 'group',
        name: 'LabOperators',
        policy_id: 2,
        policy_name: 'ReadOnlyAccess',
        group_id: 3,
        group_name: 'LabOperators',
      },
    ],
  },
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
  window.history.pushState({}, '', '/iam/users/new');
  storeToken('owner-token');
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('IAM user creation workflow', () => {
  it('creates a user with a group, exposes the temporary password once, and opens enforced details', async () => {
    fetchMock.mockImplementation(async (url, options = {}) => {
      if (url.endsWith('/auth/me')) {
        return jsonResponse(owner);
      }
      if (url.endsWith('/iam/groups')) {
        return jsonResponse([group]);
      }
      if (url.endsWith('/iam/users') && options.method === 'POST') {
        return jsonResponse(createdUser, 201);
      }
      if (url.endsWith('/iam/users/42')) {
        return jsonResponse(createdUser);
      }
      throw new Error(`Unexpected request: ${url} (${options.method})`);
    });
    const user = userEvent.setup();

    render(<AppRoutes />);

    await user.type(await screen.findByLabelText('Username'), 'Student2');
    await user.type(screen.getByLabelText('Display name'), 'Student Two');
    await user.type(
      screen.getByLabelText('Temporary password', { exact: true }),
      'temporary-pass-123',
    );
    await user.type(
      screen.getByLabelText('Confirm temporary password'),
      'temporary-pass-123',
    );
    await user.click(
      screen.getByRole('checkbox', { name: /LabOperators/ }),
    );
    await user.click(screen.getByRole('button', { name: 'Create IAM user' }));

    expect(
      await screen.findByRole('heading', { name: 'IAM user created' }),
    ).toBeInTheDocument();
    expect(screen.getByText('student2 is ready to sign in')).toBeInTheDocument();
    expect(screen.getByText('temporary-pass-123')).toBeInTheDocument();
    expect(screen.getByText('123456789012')).toBeInTheDocument();

    const createCall = fetchMock.mock.calls.find(
      ([url, options]) =>
        url.endsWith('/iam/users') && options.method === 'POST',
    );
    expect(JSON.parse(createCall[1].body)).toEqual({
      username: 'student2',
      display_name: 'Student Two',
      password: 'temporary-pass-123',
      confirm_password: 'temporary-pass-123',
      console_access_enabled: true,
      must_change_password: true,
      group_ids: [3],
    });

    await user.click(screen.getByRole('button', { name: 'View user details' }));

    expect(
      await screen.findByRole('heading', { name: 'Student Two' }),
    ).toBeInTheDocument();
    expect(screen.getByText(/IAM user/)).toBeInTheDocument();
    expect(screen.getByText('LabOperators')).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: 'Groups & permissions' }));
    expect(screen.getByText('Effective permissions (2)')).toBeInTheDocument();
    expect(screen.getByText('compute:ListInstances')).toBeInTheDocument();
    expect(screen.getAllByText('ReadOnlyAccess').length).toBeGreaterThan(0);
  });
});

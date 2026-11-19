import { render, screen, within } from '@testing-library/react';
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

const candidate = {
  id: 42,
  account_id: '123456789012',
  username: 'student2',
  display_name: 'Student Two',
  status: 'active',
  console_access_enabled: true,
  must_change_password: true,
  groups: [],
  created_at: '2026-11-16T10:00:00Z',
  updated_at: '2026-11-16T10:00:00Z',
  last_login_at: null,
};

const policy = {
  id: 2,
  name: 'ReadOnlyAccess',
  description: 'Read-only lab access.',
  version: 1,
  is_managed: true,
  group_count: 0,
  actions: ['dashboard:Read', 'compute:ListInstances'],
  action_descriptions: {
    'dashboard:Read': 'View the console dashboard and account resource totals.',
    'compute:ListInstances': 'List compute instances.',
  },
  created_at: '2026-11-16T09:00:00Z',
  updated_at: '2026-11-16T09:00:00Z',
};

function groupState({ members = [], policies = [] } = {}) {
  return {
    id: 3,
    name: 'LabOperators',
    description: 'Operate the compute lab.',
    user_count: members.length,
    policy_count: policies.length,
    members,
    policies,
    created_at: '2026-11-16T10:00:00Z',
    updated_at: '2026-11-16T10:00:00Z',
  };
}

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async () => body,
  };
}

const emptyGroup = groupState();
const memberGroup = groupState({
  members: [
    {
      id: 42,
      username: 'student2',
      display_name: 'Student Two',
      status: 'active',
      console_access_enabled: true,
    },
  ],
});
const policyGroup = groupState({
  members: memberGroup.members,
  policies: [policy],
});

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  window.localStorage.clear();
  window.history.pushState({}, '', '/iam/groups/3');
  storeToken('owner-token');
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('IAM group membership and policy workflow', () => {
  it('adds an existing user, attaches a policy, and detaches it through real API calls', async () => {
    fetchMock.mockImplementation(async (url, options = {}) => {
      const method = options.method || 'GET';
      if (url.endsWith('/auth/me')) {
        return jsonResponse(owner);
      }
      if (url.endsWith('/iam/groups/3') && method === 'GET') {
        return jsonResponse(emptyGroup);
      }
      if (url.endsWith('/iam/users') && method === 'GET') {
        return jsonResponse([candidate]);
      }
      if (url.endsWith('/iam/groups/3/users') && method === 'POST') {
        return jsonResponse(memberGroup);
      }
      if (url.endsWith('/iam/policies') && method === 'GET') {
        return jsonResponse([policy]);
      }
      if (url.endsWith('/iam/groups/3/policies') && method === 'POST') {
        return jsonResponse(policyGroup);
      }
      if (url.endsWith('/iam/groups/3/policies/2') && method === 'DELETE') {
        return jsonResponse(memberGroup);
      }
      throw new Error(`Unexpected request: ${method} ${url}`);
    });
    const user = userEvent.setup();

    render(<AppRoutes />);

    expect(
      await screen.findByRole('heading', { name: 'LabOperators' }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: 'Members (0)' }));
    await user.click(screen.getByRole('button', { name: 'Add users' }));
    await user.click(
      await screen.findByRole('checkbox', { name: /Student Two/ }),
    );
    await user.click(screen.getByRole('button', { name: 'Add 1 user' }));

    expect(await screen.findByText(/1 IAM user\(s\) added/)).toBeInTheDocument();
    expect(screen.getByText('student2')).toBeInTheDocument();
    const addCall = fetchMock.mock.calls.find(
      ([url, options]) =>
        url.endsWith('/iam/groups/3/users') && options.method === 'POST',
    );
    expect(JSON.parse(addCall[1].body)).toEqual({ user_ids: [42] });

    await user.click(screen.getByRole('tab', { name: 'Policies (0)' }));
    await user.click(screen.getByRole('button', { name: 'Attach policies' }));
    await user.click(
      await screen.findByRole('checkbox', { name: /ReadOnlyAccess/ }),
    );
    await user.click(screen.getByRole('button', { name: 'Attach 1 policy' }));

    expect(
      await screen.findByText(/1 policy\(ies\) attached/),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'ReadOnlyAccess' })).toBeInTheDocument();
    const attachCall = fetchMock.mock.calls.find(
      ([url, options]) =>
        url.endsWith('/iam/groups/3/policies') && options.method === 'POST',
    );
    expect(JSON.parse(attachCall[1].body)).toEqual({ policy_ids: [2] });

    await user.click(screen.getByRole('button', { name: 'Detach' }));
    const detachDialog = await screen.findByRole('dialog');
    await user.click(
      within(detachDialog).getByRole('button', { name: 'Detach policy' }),
    );

    expect(
      await screen.findByText(/ReadOnlyAccess detached/),
    ).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(
        ([url, options]) =>
          url.endsWith('/iam/groups/3/policies/2') &&
          options.method === 'DELETE',
      ),
    ).toBe(true);
    expect(
      screen.queryByRole('link', { name: 'ReadOnlyAccess' }),
    ).not.toBeInTheDocument();
  });

  it('keeps the policy attached when detaching is cancelled', async () => {
    fetchMock.mockImplementation(async (url, options = {}) => {
      const method = options.method || 'GET';
      if (url.endsWith('/auth/me')) {
        return jsonResponse(owner);
      }
      if (url.endsWith('/iam/groups/3') && method === 'GET') {
        return jsonResponse(policyGroup);
      }
      throw new Error(`Unexpected request: ${method} ${url}`);
    });
    const user = userEvent.setup();

    render(<AppRoutes />);

    expect(
      await screen.findByRole('heading', { name: 'LabOperators' }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: 'Policies (1)' }));
    expect(
      screen.getByRole('link', { name: 'ReadOnlyAccess' }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Detach' }));
    const detachDialog = await screen.findByRole('dialog');
    expect(
      within(detachDialog).getByText(
        /ReadOnlyAccess will stop granting access/,
      ),
    ).toBeInTheDocument();

    await user.click(
      within(detachDialog).getByRole('button', { name: 'Cancel' }),
    );

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'ReadOnlyAccess' }),
    ).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(
        ([url, options]) =>
          url.endsWith('/iam/groups/3/policies/2') &&
          options.method === 'DELETE',
      ),
    ).toBe(false);
  });
});

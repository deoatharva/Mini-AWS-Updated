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

const actions = [
  {
    action: 'dashboard:Read',
    description: 'View the console dashboard and account resource totals.',
    category: 'dashboard',
  },
  {
    action: 'compute:ListInstances',
    description: 'List compute instances.',
    category: 'compute',
  },
  {
    action: 'compute:CreateInstance',
    description: 'Create compute instances.',
    category: 'compute',
  },
  {
    action: 'storage:ListBuckets',
    description: 'List storage buckets.',
    category: 'storage',
  },
];

function policyState({ version = 1, actionList = ['compute:ListInstances'] } = {}) {
  return {
    id: 9,
    name: 'LabComputeAccess',
    description: 'Allows selected compute lab actions.',
    version,
    is_managed: false,
    group_count: 0,
    actions: actionList,
    action_descriptions: Object.fromEntries(
      actions
        .filter((item) => actionList.includes(item.action))
        .map((item) => [item.action, item.description]),
    ),
    created_at: '2026-11-16T11:00:00Z',
    updated_at: version > 1
      ? '2026-11-16T12:00:00Z'
      : '2026-11-16T11:00:00Z',
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

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  window.localStorage.clear();
  window.history.pushState({}, '', '/iam/policies/new');
  storeToken('owner-token');
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('custom policy workflow', () => {
  it('creates, edits, and deletes a custom policy with exact selected actions', async () => {
    const createdPolicy = policyState({
      actionList: ['compute:CreateInstance', 'compute:ListInstances'],
    });
    const updatedPolicy = policyState({
      version: 2,
      actionList: [
        'compute:CreateInstance',
        'compute:ListInstances',
        'storage:ListBuckets',
      ],
    });
    fetchMock.mockImplementation(async (url, options = {}) => {
      const method = options.method || 'GET';
      if (url.endsWith('/auth/me')) {
        return jsonResponse(owner);
      }
      if (url.endsWith('/iam/actions') && method === 'GET') {
        return jsonResponse(actions);
      }
      if (url.endsWith('/iam/policies') && method === 'POST') {
        return jsonResponse(createdPolicy, 201);
      }
      if (url.endsWith('/iam/policies/9') && method === 'GET') {
        return jsonResponse(createdPolicy);
      }
      if (url.endsWith('/iam/policies/9') && method === 'PATCH') {
        return jsonResponse(updatedPolicy);
      }
      if (url.endsWith('/iam/policies/9') && method === 'DELETE') {
        return jsonResponse(null, 204);
      }
      if (url.endsWith('/iam/policies') && method === 'GET') {
        return jsonResponse([updatedPolicy]);
      }
      throw new Error(`Unexpected request: ${method} ${url}`);
    });
    const user = userEvent.setup();

    render(<AppRoutes />);

    await user.type(
      await screen.findByLabelText('Policy name'),
      'LabComputeAccess',
    );
    await user.type(
      screen.getByLabelText('Description'),
      'Allows selected compute lab actions.',
    );
    await user.click(
      screen.getByRole('checkbox', { name: /compute:ListInstances/ }),
    );
    await user.click(
      screen.getByRole('checkbox', { name: /compute:CreateInstance/ }),
    );
    await user.click(screen.getByRole('button', { name: 'Create policy' }));

    expect(
      await screen.findByRole('heading', { name: 'LabComputeAccess' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Policy created.')).toBeInTheDocument();

    const createCall = fetchMock.mock.calls.find(
      ([url, options]) =>
        url.endsWith('/iam/policies') && options.method === 'POST',
    );
    expect(JSON.parse(createCall[1].body)).toEqual({
      name: 'LabComputeAccess',
      description: 'Allows selected compute lab actions.',
      actions: ['compute:ListInstances', 'compute:CreateInstance'],
    });

    await user.click(screen.getByRole('button', { name: 'Edit policy' }));
    await user.click(
      screen.getByRole('checkbox', { name: /storage:ListBuckets/ }),
    );
    await user.click(screen.getByRole('button', { name: 'Save policy' }));

    expect(
      await screen.findByText(/Custom policy updated/),
    ).toBeInTheDocument();
    const patchCall = fetchMock.mock.calls.find(
      ([url, options]) =>
        url.endsWith('/iam/policies/9') && options.method === 'PATCH',
    );
    expect(JSON.parse(patchCall[1].body)).toEqual({
      name: 'LabComputeAccess',
      description: 'Allows selected compute lab actions.',
      actions: [
        'compute:CreateInstance',
        'compute:ListInstances',
        'storage:ListBuckets',
      ],
    });

    await user.click(screen.getByRole('button', { name: 'Delete' }));
    const dialog = await screen.findByRole('dialog');
    await user.click(
      within(dialog).getByRole('button', { name: 'Delete policy' }),
    );

    expect(
      await screen.findByRole('heading', { name: 'IAM policies' }),
    ).toBeInTheDocument();
    expect(window.location.pathname).toBe('/iam/policies');
    expect(
      fetchMock.mock.calls.some(
        ([url, options]) =>
          url.endsWith('/iam/policies/9') && options.method === 'DELETE',
      ),
    ).toBe(true);
  });
});

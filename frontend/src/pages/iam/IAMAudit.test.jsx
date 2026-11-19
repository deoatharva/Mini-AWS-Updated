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

const successEvent = {
  id: 1,
  account_id: '123456789012',
  actor_user_id: 8,
  actor_username: 'student2',
  actor_display_name: 'Student Two',
  actor_type: 'IAM',
  event_type: 'iam.user.created',
  target_type: 'iam_user',
  target_id: '42',
  success: true,
  metadata: { username: 'student2', password: '[redacted]' },
  created_at: '2026-11-16T12:00:00Z',
};

const failedEvent = {
  ...successEvent,
  id: 2,
  event_type: 'iam.user.updated',
  success: false,
  metadata: { target_username: 'student2', change: 'display_name' },
  created_at: '2026-11-16T12:10:00Z',
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
  window.history.pushState({}, '', '/iam/audit');
  storeToken('owner-token');
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('IAM audit log page', () => {
  it('shows account-scoped events, redacted metadata, and applies server filters', async () => {
    fetchMock.mockImplementation(async (url) => {
      if (url.endsWith('/auth/me')) {
        return jsonResponse(owner);
      }
      if (url.includes('/iam/audit-logs')) {
        return jsonResponse(
          url.includes('success=false') ? [failedEvent] : [successEvent],
        );
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    const user = userEvent.setup();

    render(<AppRoutes />);

    const table = await screen.findByRole('table');
    expect(within(table).getByText('IAM user created')).toBeInTheDocument();
    expect(within(table).getByText('student2')).toBeInTheDocument();
    expect(within(table).getByText('Success')).toBeInTheDocument();
    expect(within(table).getByText(/\[redacted\]/)).toBeInTheDocument();

    await user.type(
      screen.getByLabelText('Search actor, target, or details'),
      'student2',
    );
    await user.selectOptions(
      screen.getByLabelText('Event type'),
      'iam.user.updated',
    );
    await user.selectOptions(screen.getByLabelText('Result'), 'false');
    await user.click(screen.getByRole('button', { name: 'Apply filters' }));

    expect(
      await within(await screen.findByRole('table')).findByText('IAM user updated'),
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole('table')).getByText('Failed'),
    ).toBeInTheDocument();

    const auditCalls = fetchMock.mock.calls
      .map(([url]) => url)
      .filter((url) => url.includes('/iam/audit-logs'));
    expect(auditCalls.length).toBe(2);
    expect(auditCalls[1]).toContain('q=student2');
    expect(auditCalls[1]).toContain('event_type=iam.user.updated');
    expect(auditCalls[1]).toContain('success=false');
    expect(auditCalls[1]).toContain('limit=100');
  });
});

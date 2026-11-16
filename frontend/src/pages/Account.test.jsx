import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../auth/AuthContext.jsx';
import { storeToken } from '../services/api.js';
import Account from './Account.jsx';

const fetchMock = vi.fn();

const account = {
  id: 4,
  name: 'Demo Student',
  email: 'demo@example.com',
  created_at: '2026-11-16T09:00:00Z',
};

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async () => body,
  };
}

function renderAccount() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <Account />
      </AuthProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  window.localStorage.clear();
  storeToken('test-token');
});

describe('account page', () => {
  it('updates the display name through the API', async () => {
    fetchMock.mockImplementation(async (url, options = {}) => {
      if (url.endsWith('/auth/me') && options.method === 'PATCH') {
        return jsonResponse({ ...account, name: 'Renamed Student' });
      }
      if (url.endsWith('/auth/me')) {
        return jsonResponse(account);
      }
      throw new Error(`Unexpected request: ${url}`);
    });

    const user = userEvent.setup();
    renderAccount();

    const input = await screen.findByDisplayValue('Demo Student');
    expect(input).toHaveAccessibleName('Name');
    await user.clear(input);
    await user.type(input, 'Renamed Student');
    await user.click(screen.getByRole('button', { name: 'Save name' }));

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Display name updated.',
    );
    expect(screen.getAllByText('Renamed Student').length).toBeGreaterThan(0);
    expect(input).toHaveValue('Renamed Student');

    const patchCall = fetchMock.mock.calls.find(
      ([url, options]) => url.endsWith('/auth/me') && options.method === 'PATCH',
    );
    expect(JSON.parse(patchCall[1].body)).toEqual({ name: 'Renamed Student' });
    expect(patchCall[1].headers.Authorization).toBe('Bearer test-token');
  });

  it('changes the password and clears the password fields', async () => {
    fetchMock.mockImplementation(async (url, options = {}) => {
      if (url.endsWith('/auth/password') && options.method === 'POST') {
        return jsonResponse(null, 204);
      }
      if (url.endsWith('/auth/me')) {
        return jsonResponse(account);
      }
      throw new Error(`Unexpected request: ${url}`);
    });

    const user = userEvent.setup();
    renderAccount();

    await screen.findByLabelText('Current password');
    await user.type(screen.getByLabelText('Current password'), 'old-password-123');
    await user.type(screen.getByLabelText('New password'), 'new-password-456');
    await user.type(
      screen.getByLabelText('Confirm new password'),
      'new-password-456',
    );
    await user.click(screen.getByRole('button', { name: 'Update password' }));

    expect(await screen.findByRole('status')).toHaveTextContent(
      'Password updated.',
    );
    expect(screen.getByLabelText('Current password')).toHaveValue('');
    expect(screen.getByLabelText('New password')).toHaveValue('');

    const postCall = fetchMock.mock.calls.find(([url]) =>
      url.endsWith('/auth/password'),
    );
    expect(JSON.parse(postCall[1].body)).toEqual({
      current_password: 'old-password-123',
      new_password: 'new-password-456',
    });
  });

  it('rejects mismatched new passwords without calling the API', async () => {
    fetchMock.mockImplementation(async (url) => {
      if (url.endsWith('/auth/me')) {
        return jsonResponse(account);
      }
      throw new Error(`Unexpected request: ${url}`);
    });

    const user = userEvent.setup();
    renderAccount();

    await screen.findByLabelText('Current password');
    await user.type(screen.getByLabelText('Current password'), 'old-password-123');
    await user.type(screen.getByLabelText('New password'), 'new-password-456');
    await user.type(
      screen.getByLabelText('Confirm new password'),
      'different-password-789',
    );
    await user.click(screen.getByRole('button', { name: 'Update password' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The new passwords do not match.',
    );
    expect(
      fetchMock.mock.calls.some(([url]) => url.endsWith('/auth/password')),
    ).toBe(false);
  });
});

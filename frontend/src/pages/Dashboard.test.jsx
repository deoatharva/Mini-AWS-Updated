import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../auth/AuthContext.jsx';
import { storeToken } from '../services/api.js';
import Dashboard from './Dashboard.jsx';

const fetchMock = vi.fn();

const account = {
  id: 1,
  name: 'Demo Student',
  email: 'demo@example.com',
  created_at: '2026-11-16T09:00:00Z',
};

const summary = {
  counts: {
    compute_total: 3,
    compute_running: 2,
    applications_total: 1,
    applications_running: 1,
    buckets_total: 2,
    objects_total: 4,
    storage_bytes: 2048,
    databases_total: 2,
  },
  recent_activity: [
    {
      id: 'compute_instance-1',
      service: 'compute',
      action: 'started',
      resource_type: 'compute_instance',
      resource_id: 1,
      resource_name: 'Lab host',
      timestamp: '2026-11-16T10:30:00Z',
    },
    {
      id: 'object-7',
      service: 'storage',
      action: 'uploaded',
      resource_type: 'object',
      resource_id: 7,
      resource_name: 'practical-bucket/notes.txt',
      timestamp: '2026-11-16T10:20:00Z',
    },
    {
      id: 'bucket-3',
      service: 'storage',
      action: 'deleted',
      resource_type: 'bucket',
      resource_id: 3,
      resource_name: 'old-bucket',
      timestamp: '2026-11-16T10:10:00Z',
    },
  ],
};

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async () => body,
  };
}

function renderDashboard() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <Dashboard />
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

describe('dashboard page', () => {
  it('shows real resource counts and recent activity from the API', async () => {
    fetchMock.mockImplementation(async (url) => {
      if (url.endsWith('/auth/me')) {
        return jsonResponse(account);
      }
      if (url.endsWith('/dashboard')) {
        return jsonResponse(summary);
      }
      throw new Error(`Unexpected request: ${url}`);
    });

    renderDashboard();

    expect(
      await screen.findByRole('heading', { name: 'Welcome back, Demo Student' }),
    ).toBeInTheDocument();

    expect(await screen.findByText('2 / 3')).toBeInTheDocument();
    expect(screen.getByText('1 / 1')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('2 buckets · 2.0 KB')).toBeInTheDocument();

    expect(screen.getByText(/Started/)).toBeInTheDocument();
    expect(screen.getByText('Lab host')).toBeInTheDocument();
    expect(screen.getByText(/Uploaded/)).toBeInTheDocument();
    expect(screen.getByText('practical-bucket/notes.txt')).toBeInTheDocument();
    expect(screen.getByText(/Deleted/)).toBeInTheDocument();
    expect(screen.getByText('old-bucket')).toBeInTheDocument();

    const dashboardCall = fetchMock.mock.calls.find(([url]) =>
      url.endsWith('/dashboard'),
    );
    expect(dashboardCall[1].headers.Authorization).toBe('Bearer test-token');
  });

  it('shows an honest error when dashboard data cannot be loaded', async () => {
    fetchMock.mockImplementation(async (url) => {
      if (url.endsWith('/auth/me')) {
        return jsonResponse(account);
      }
      if (url.endsWith('/dashboard')) {
        return jsonResponse(
          {
            error: {
              code: 'internal_error',
              message: 'An unexpected error occurred.',
            },
          },
          500,
        );
      }
      throw new Error(`Unexpected request: ${url}`);
    });

    renderDashboard();

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Could not load dashboard data',
    );
    expect(screen.queryByText('2 / 3')).not.toBeInTheDocument();
    expect(screen.getByText('No activity yet')).toBeInTheDocument();
  });

  it('reloads the summary with the refresh button', async () => {
    fetchMock.mockImplementation(async (url) => {
      if (url.endsWith('/auth/me')) {
        return jsonResponse(account);
      }
      if (url.endsWith('/dashboard')) {
        const isRefresh = fetchMock.mock.calls.filter(([callUrl]) =>
          callUrl.endsWith('/dashboard'),
        ).length > 1;
        if (isRefresh) {
          return jsonResponse({
            counts: {
              ...summary.counts,
              compute_running: 3,
              databases_total: 3,
            },
            recent_activity: [],
          });
        }
        return jsonResponse(summary);
      }
      throw new Error(`Unexpected request: ${url}`);
    });

    const user = userEvent.setup();
    renderDashboard();

    expect(await screen.findByText('2 / 3')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Refresh' }));

    expect(await screen.findByText('3 / 3')).toBeInTheDocument();
    expect(screen.getByText('No activity yet')).toBeInTheDocument();
  });
});

import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { storeToken } from '../../services/api.js';
import Applications from './Applications.jsx';

const fetchMock = vi.fn();

const stoppedDeployment = {
  id: 1,
  name: 'Practical app',
  template: 'sample-web-app',
  status: 'stopped',
  port: null,
  pid: null,
  local_url: null,
  last_error: null,
  created_at: '2026-11-16T10:00:00Z',
  updated_at: '2026-11-16T10:00:00Z',
  started_at: null,
  stopped_at: null,
};

const runningDeployment = {
  ...stoppedDeployment,
  status: 'running',
  port: 19001,
  pid: 5252,
  local_url: 'http://127.0.0.1:19001/',
  started_at: '2026-11-16T10:01:00Z',
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
  storeToken('test-token');
});

describe('application deployment page', () => {
  it('shows real running state and local URL from the API', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse([runningDeployment]));

    render(<Applications />);

    expect(await screen.findByText('Practical app')).toBeInTheDocument();
    expect(screen.getByText('Running')).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /127\.0\.0\.1:19001/ }),
    ).toHaveAttribute('href', 'http://127.0.0.1:19001/');

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers.Authorization).toBe('Bearer test-token');
  });

  it('deploys, starts, reads logs for, and deletes the sample app', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(stoppedDeployment, 201))
      .mockResolvedValueOnce(jsonResponse(runningDeployment))
      .mockResolvedValueOnce(
        jsonResponse({
          content: '[app] deployment 1 listening on http://127.0.0.1:19001/',
          truncated: false,
        }),
      )
      .mockResolvedValueOnce(emptyResponse(204));

    const user = userEvent.setup();
    render(<Applications />);

    expect(await screen.findByText('No applications deployed')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Deploy application' }));

    const dialog = screen.getByRole('dialog', {
      name: 'Deploy sample application',
    });
    await user.type(within(dialog).getByLabelText('Application name'), 'Practical app');
    await user.click(
      within(dialog).getByRole('button', { name: 'Deploy application' }),
    );

    expect(await screen.findByText('Practical app')).toBeInTheDocument();
    expect(screen.getByText('Running')).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /127\.0\.0\.1:19001/ }),
    ).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Logs' }));
    expect(
      await screen.findByText(/\[app\] deployment 1 listening/),
    ).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Close' }));

    await user.click(screen.getByRole('button', { name: 'Delete' }));
    const deleteDialog = screen.getByRole('dialog', {
      name: 'Delete application',
    });
    await user.click(
      within(deleteDialog).getByRole('button', { name: 'Delete application' }),
    );

    expect(await screen.findByText('No applications deployed')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      expect.stringMatching(/\/applications$/),
      expect.objectContaining({ method: 'POST' }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      expect.stringMatching(/\/applications\/1\/start$/),
      expect.objectContaining({ method: 'POST' }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      5,
      expect.stringMatching(/\/applications\/1$/),
      expect.objectContaining({ method: 'DELETE' }),
    );
  });

  it('surfaces a failed start and reloads the honest error state', async () => {
    const failedDeployment = {
      ...stoppedDeployment,
      status: 'error',
      last_error: 'No free local port is available in the configured range.',
    };

    fetchMock
      .mockResolvedValueOnce(jsonResponse([stoppedDeployment]))
      .mockResolvedValueOnce(
        jsonResponse(
          {
            error: {
              code: 'application_start_failed',
              message:
                'The application could not start: No free local port is available in the configured range.',
            },
          },
          503,
        ),
      )
      .mockResolvedValueOnce(jsonResponse([failedDeployment]));

    const user = userEvent.setup();
    render(<Applications />);

    await screen.findByText('Practical app');
    await user.click(screen.getByRole('button', { name: 'Start' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No free local port is available',
    );
    expect(await screen.findByText('Error')).toBeInTheDocument();
    expect(
      screen.getByText('No free local port is available in the configured range.'),
    ).toBeInTheDocument();
  });
});

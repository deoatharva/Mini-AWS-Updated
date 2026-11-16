import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { storeToken } from '../../services/api.js';
import Instances from './Instances.jsx';

const fetchMock = vi.fn();

const stoppedInstance = {
  id: 1,
  name: 'Practical worker',
  adapter: 'process',
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

const runningInstance = {
  ...stoppedInstance,
  status: 'running',
  port: 18001,
  pid: 4242,
  local_url: 'http://127.0.0.1:18001/',
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

describe('compute instances page', () => {
  it('loads instances with the authenticated API client and reports real state', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse([stoppedInstance]));

    render(<Instances />);

    expect(await screen.findByText('Practical worker')).toBeInTheDocument();
    expect(screen.getByText('Stopped')).toBeInTheDocument();
    expect(screen.getAllByText('Local process').length).toBeGreaterThan(0);
    expect(screen.getByText('Not a virtual machine')).toBeInTheDocument();

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/compute\/instances$/);
    expect(options.headers.Authorization).toBe('Bearer test-token');
  });

  it('creates, starts, reads logs for, and deletes a real instance through the API', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(stoppedInstance, 201))
      .mockResolvedValueOnce(jsonResponse(runningInstance))
      .mockResolvedValueOnce(
        jsonResponse({
          content: '[worker] instance 1 listening on http://127.0.0.1:18001/',
          truncated: false,
        }),
      )
      .mockResolvedValueOnce(emptyResponse(204));

    const user = userEvent.setup();
    render(<Instances />);

    expect(await screen.findByText('No compute instances yet')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Launch instance' }));
    await user.type(await screen.findByLabelText('Name'), 'Practical worker');
    await user.click(screen.getByRole('button', { name: 'Create instance' }));

    expect(await screen.findByText('Practical worker')).toBeInTheDocument();
    expect(screen.getByText('Stopped')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Start' }));
    expect(await screen.findByText('Running')).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /127\.0\.0\.1:18001/ }),
    ).toHaveAttribute('href', 'http://127.0.0.1:18001/');

    await user.click(screen.getByRole('button', { name: 'Logs' }));
    expect(
      await screen.findByText(/\[worker\] instance 1 listening/),
    ).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Close' }));

    await user.click(screen.getByRole('button', { name: 'Delete' }));
    expect(
      screen.getByRole('dialog', { name: 'Delete instance' }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Delete instance' }));

    expect(await screen.findByText('No compute instances yet')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      expect.stringMatching(/\/compute\/instances$/),
      expect.objectContaining({ method: 'POST' }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      expect.stringMatching(/\/compute\/instances\/1\/start$/),
      expect.objectContaining({ method: 'POST' }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      4,
      expect.stringMatching(/\/compute\/instances\/1\/logs$/),
      expect.objectContaining({ method: 'GET' }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      5,
      expect.stringMatching(/\/compute\/instances\/1$/),
      expect.objectContaining({ method: 'DELETE' }),
    );
  });

  it('surfaces a start failure and reloads the honest error state', async () => {
    const failedInstance = {
      ...stoppedInstance,
      status: 'error',
      last_error: 'No free local port is available in the configured range.',
    };

    fetchMock
      .mockResolvedValueOnce(jsonResponse([stoppedInstance]))
      .mockResolvedValueOnce(
        jsonResponse(
          {
            error: {
              code: 'instance_start_failed',
              message:
                'The instance could not start: No free local port is available in the configured range.',
            },
          },
          503,
        ),
      )
      .mockResolvedValueOnce(jsonResponse([failedInstance]));

    const user = userEvent.setup();
    render(<Instances />);

    await screen.findByText('Practical worker');
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

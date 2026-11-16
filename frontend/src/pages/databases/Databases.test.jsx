import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { storeToken } from '../../services/api.js';
import Databases from './Databases.jsx';

const fetchMock = vi.fn();

const emptyDatabase = {
  id: 1,
  name: 'Practical DB',
  engine: 'sqlite',
  status: 'available',
  table_count: 0,
  last_error: null,
  created_at: '2026-11-16T10:00:00Z',
  updated_at: '2026-11-16T10:00:00Z',
};

const notesTable = {
  name: 'notes',
  kind: 'table',
  columns: [
    { name: 'id', type: 'INTEGER', not_null: false, default_value: null, primary_key: true },
    { name: 'title', type: 'TEXT', not_null: true, default_value: null, primary_key: false },
  ],
};

const selectResult = {
  columns: ['id', 'title'],
  rows: [
    [1, 'First note'],
    [2, 'Second note'],
  ],
  rows_affected: 0,
  duration_ms: 0.42,
  truncated: false,
  statement_type: 'SELECT',
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

describe('databases page', () => {
  it('opens a database, shows its schema, and runs a real SQL query', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse([{ ...emptyDatabase, table_count: 1 }]))
      .mockResolvedValueOnce(jsonResponse([notesTable]))
      .mockResolvedValueOnce(jsonResponse(selectResult))
      .mockResolvedValueOnce(jsonResponse([{ ...emptyDatabase, table_count: 1 }]))
      .mockResolvedValueOnce(jsonResponse([notesTable]));

    const user = userEvent.setup();
    render(<Databases />);

    expect(await screen.findByText('Practical DB')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Open SQL' }));

    expect(await screen.findByText('notes')).toBeInTheDocument();
    expect(screen.getByText('table · 2 columns')).toBeInTheDocument();

    await user.type(
      screen.getByLabelText('SQL statement'),
      'SELECT id, title FROM notes',
    );
    await user.click(screen.getByRole('button', { name: 'Run query' }));

    expect(await screen.findByText('First note')).toBeInTheDocument();
    expect(screen.getByText('Second note')).toBeInTheDocument();
    expect(screen.getByText('id')).toBeInTheDocument();
    expect(screen.getByText('title')).toBeInTheDocument();
    expect(screen.getByText(/SELECT · 2 rows returned/)).toBeInTheDocument();

    const [queryUrl, queryOptions] = fetchMock.mock.calls[2];
    expect(queryUrl).toMatch(/\/databases\/1\/query$/);
    expect(queryOptions.method).toBe('POST');
    expect(queryOptions.headers.Authorization).toBe('Bearer test-token');
    expect(JSON.parse(queryOptions.body)).toEqual({
      sql: 'SELECT id, title FROM notes',
    });
  });

  it('creates a database and deletes it from the list', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(emptyDatabase, 201))
      .mockResolvedValueOnce(emptyResponse(204));

    const user = userEvent.setup();
    render(<Databases />);

    expect(await screen.findByText('No databases to display')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Create database' }));

    const dialog = screen.getByRole('dialog', { name: 'Create database' });
    await user.type(
      within(dialog).getByLabelText('Database name'),
      'Practical DB',
    );
    await user.click(
      within(dialog).getByRole('button', { name: 'Create database' }),
    );

    expect(await screen.findByText('Practical DB')).toBeInTheDocument();
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({
      name: 'Practical DB',
    });

    await user.click(
      screen.getByRole('button', { name: 'Delete database Practical DB' }),
    );
    const deleteDialog = screen.getByRole('dialog', { name: 'Delete database' });
    await user.click(
      within(deleteDialog).getByRole('button', { name: 'Delete database' }),
    );

    expect(await screen.findByText('No databases to display')).toBeInTheDocument();
    expect(fetchMock.mock.calls[2][0]).toMatch(/\/databases\/1$/);
    expect(fetchMock.mock.calls[2][1].method).toBe('DELETE');
  });

  it('shows an honest SQL error without inventing results', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse([emptyDatabase]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(
        jsonResponse(
          {
            error: {
              code: 'sql_error',
              message: 'SQLite: no such table: missing_table',
            },
          },
          422,
        ),
      );

    const user = userEvent.setup();
    render(<Databases />);

    await screen.findByText('Practical DB');
    await user.click(screen.getByRole('button', { name: 'Open SQL' }));
    expect(
      await screen.findByText(/No tables yet/),
    ).toBeInTheDocument();

    await user.type(
      screen.getByLabelText('SQL statement'),
      'SELECT * FROM missing_table',
    );
    await user.click(screen.getByRole('button', { name: 'Run query' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'no such table: missing_table',
    );
    expect(screen.queryByText(/rows returned/)).not.toBeInTheDocument();
    expect(screen.queryByText('Statement executed')).not.toBeInTheDocument();
  });
});

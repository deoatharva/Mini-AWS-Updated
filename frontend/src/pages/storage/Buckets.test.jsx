import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { storeToken } from '../../services/api.js';
import Buckets from './Buckets.jsx';

const fetchMock = vi.fn();
let anchorClick;

const emptyBucket = {
  id: 1,
  name: 'practical-bucket',
  object_count: 0,
  total_bytes: 0,
  created_at: '2026-11-16T10:00:00Z',
};

const filledBucket = {
  ...emptyBucket,
  object_count: 1,
  total_bytes: 13,
};

const storedObject = {
  id: 7,
  bucket_id: 1,
  object_key: 'notes.txt',
  size_bytes: 13,
  content_type: 'text/plain',
  etag: 'a'.repeat(64),
  created_at: '2026-11-16T10:05:00Z',
  updated_at: '2026-11-16T10:05:00Z',
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

function blobResponse(body = new Blob(['hello storage'])) {
  return {
    ok: true,
    status: 200,
    headers: new Headers({ 'content-type': 'text/plain' }),
    blob: async () => body,
  };
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  window.localStorage.clear();
  storeToken('test-token');

  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    writable: true,
    value: vi.fn(() => 'blob:mini-aws-download'),
  });
  Object.defineProperty(URL, 'revokeObjectURL', {
    configurable: true,
    writable: true,
    value: vi.fn(),
  });
  anchorClick = vi
    .spyOn(HTMLAnchorElement.prototype, 'click')
    .mockImplementation(() => {});
});

afterEach(() => {
  anchorClick?.mockRestore();
});

describe('object storage page', () => {
  it('opens a bucket, lists real objects, and downloads with authentication', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse([filledBucket]))
      .mockResolvedValueOnce(jsonResponse([storedObject]))
      .mockResolvedValueOnce(blobResponse());

    const user = userEvent.setup();
    render(<Buckets />);

    expect(await screen.findByText('practical-bucket')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Delete bucket practical-bucket' }),
    ).toBeDisabled();

    await user.click(screen.getByRole('button', { name: 'Open' }));

    expect(await screen.findByText('notes.txt')).toBeInTheDocument();
    expect(screen.getByText('text/plain')).toBeInTheDocument();
    expect(screen.getAllByText('13 B').length).toBeGreaterThanOrEqual(2);

    await user.click(screen.getByRole('button', { name: 'Download' }));

    await waitFor(() => expect(anchorClick).toHaveBeenCalledTimes(1));
    const [downloadUrl, downloadOptions] = fetchMock.mock.calls[2];
    expect(downloadUrl).toMatch(
      /\/storage\/buckets\/1\/objects\/7\/download$/,
    );
    expect(downloadOptions.headers.Authorization).toBe('Bearer test-token');
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:mini-aws-download');
  });

  it('creates a bucket, uploads an object, deletes it, then deletes the bucket', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(emptyBucket, 201))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse(storedObject, 201))
      .mockResolvedValueOnce(jsonResponse([filledBucket]))
      .mockResolvedValueOnce(emptyResponse(204))
      .mockResolvedValueOnce(jsonResponse([emptyBucket]))
      .mockResolvedValueOnce(emptyResponse(204));

    const user = userEvent.setup();
    const file = new File(['hello storage'], 'notes.txt', { type: 'text/plain' });
    render(<Buckets />);

    expect(await screen.findByText('No buckets to display')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Create bucket' }));

    const createDialog = screen.getByRole('dialog', { name: 'Create bucket' });
    await user.type(
      within(createDialog).getByLabelText('Bucket name'),
      'Practical-Bucket',
    );
    await user.click(
      within(createDialog).getByRole('button', { name: 'Create bucket' }),
    );

    expect(await screen.findByText('practical-bucket')).toBeInTheDocument();
    const createOptions = fetchMock.mock.calls[1][1];
    expect(JSON.parse(createOptions.body)).toEqual({ name: 'practical-bucket' });

    await user.click(screen.getByRole('button', { name: 'Open' }));
    expect(await screen.findByText('This bucket is empty')).toBeInTheDocument();

    await user.upload(screen.getByLabelText('Choose a file to upload'), file);
    await user.click(screen.getByRole('button', { name: 'Upload object' }));

    expect(await screen.findByText('notes.txt')).toBeInTheDocument();
    const uploadOptions = fetchMock.mock.calls[3][1];
    expect(uploadOptions.body).toBeInstanceOf(FormData);
    const uploadedFile = uploadOptions.body.get('file');
    expect(uploadedFile.name).toBe('notes.txt');
    expect(uploadedFile.size).toBe(file.size);
    expect(
      screen.getByRole('button', { name: 'Delete bucket practical-bucket' }),
    ).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Delete object notes.txt' })).toBeInTheDocument();

    await user.click(
      screen.getByRole('button', { name: 'Delete object notes.txt' }),
    );
    const deleteObjectDialog = screen.getByRole('dialog', {
      name: 'Delete object',
    });
    await user.click(
      within(deleteObjectDialog).getByRole('button', { name: 'Delete object' }),
    );

    await waitFor(() => expect(screen.queryByText('notes.txt')).not.toBeInTheDocument());
    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: 'Delete bucket practical-bucket' }),
      ).toBeEnabled(),
    );

    await user.click(
      screen.getByRole('button', { name: 'Delete bucket practical-bucket' }),
    );
    const deleteBucketDialog = screen.getByRole('dialog', {
      name: 'Delete bucket',
    });
    await user.click(
      within(deleteBucketDialog).getByRole('button', { name: 'Delete bucket' }),
    );

    expect(await screen.findByText('No buckets to display')).toBeInTheDocument();
    expect(fetchMock.mock.calls[7][0]).toMatch(/\/storage\/buckets\/1$/);
    expect(fetchMock.mock.calls[7][1].method).toBe('DELETE');
  });

  it('shows an honest upload error and keeps the object list empty', async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse([emptyBucket]))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(
        jsonResponse(
          {
            error: {
              code: 'file_too_large',
              message: 'Files must be at most 4 bytes.',
            },
          },
          413,
        ),
      );

    const user = userEvent.setup();
    render(<Buckets />);

    await screen.findByText('practical-bucket');
    await user.click(screen.getByRole('button', { name: 'Open' }));
    await screen.findByText('This bucket is empty');

    const file = new File(['12345'], 'large.txt', { type: 'text/plain' });
    await user.upload(screen.getByLabelText('Choose a file to upload'), file);
    await user.click(screen.getByRole('button', { name: 'Upload object' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Files must be at most 4 bytes.',
    );
    expect(screen.queryByText('large.txt')).not.toBeInTheDocument();
    expect(screen.getByText('This bucket is empty')).toBeInTheDocument();
  });
});

import {
  Download,
  FileUp,
  FolderOpen,
  HardDrive,
  Plus,
  RefreshCw,
  Trash2,
} from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

import { Modal } from '../../components/Modal.jsx';
import { api, getErrorMessage } from '../../services/api.js';
import { formatBytes, formatDateTime } from '../../utils/format.js';

export default function Buckets() {
  const [buckets, setBuckets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [modal, setModal] = useState(null);
  const [bucketName, setBucketName] = useState('');
  const [createError, setCreateError] = useState('');
  const [creating, setCreating] = useState(false);
  const [selectedBucket, setSelectedBucket] = useState(null);
  const [objects, setObjects] = useState([]);
  const [objectsLoading, setObjectsLoading] = useState(false);
  const [objectsError, setObjectsError] = useState('');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [selectedObject, setSelectedObject] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [downloadingId, setDownloadingId] = useState(null);
  const fileInputRef = useRef(null);

  const refreshBuckets = useCallback(async ({ quiet = false } = {}) => {
    if (!quiet) {
      setLoading(true);
    }
    try {
      const data = await api.storage.listBuckets();
      setBuckets(data);
      setLoadError('');
      setSelectedBucket((current) =>
        current ? data.find((bucket) => bucket.id === current.id) || null : null,
      );
    } catch (requestError) {
      setLoadError(getErrorMessage(requestError));
    } finally {
      if (!quiet) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    refreshBuckets();
  }, [refreshBuckets]);

  async function loadObjects(bucketId, { quiet = false } = {}) {
    if (!quiet) {
      setObjectsLoading(true);
    }
    try {
      const data = await api.storage.listObjects(bucketId);
      setObjects(data);
      setObjectsError('');
    } catch (requestError) {
      setObjectsError(getErrorMessage(requestError));
    } finally {
      if (!quiet) {
        setObjectsLoading(false);
      }
    }
  }

  async function openBucket(bucket) {
    setSelectedBucket(bucket);
    setObjects([]);
    setObjectsError('');
    setUploadError('');
    setFile(null);
    setError('');
    setNotice('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    await loadObjects(bucket.id);
  }

  function closeBucket() {
    if (uploading) {
      return;
    }
    setSelectedBucket(null);
    setObjects([]);
    setObjectsError('');
    setUploadError('');
    setFile(null);
  }

  async function handleCreateBucket(event) {
    event.preventDefault();
    const cleaned = bucketName.trim().toLowerCase();
    if (cleaned.length < 3) {
      setCreateError('Bucket names must be at least 3 characters.');
      return;
    }

    setCreating(true);
    setCreateError('');
    setError('');
    setNotice('');
    try {
      const created = await api.storage.createBucket({ name: cleaned });
      setBuckets((current) => [created, ...current]);
      setModal(null);
      setBucketName('');
      setNotice(`Bucket "${created.name}" was created in local storage.`);
    } catch (requestError) {
      setCreateError(getErrorMessage(requestError));
    } finally {
      setCreating(false);
    }
  }

  async function handleUpload() {
    if (!selectedBucket || !file) {
      return;
    }
    setUploading(true);
    setUploadError('');
    setError('');
    setNotice('');
    try {
      const uploaded = await api.storage.uploadObject(selectedBucket.id, file);
      setObjects((current) => {
        const remaining = current.filter(
          (item) => item.object_key !== uploaded.object_key,
        );
        return [...remaining, uploaded].sort((left, right) =>
          left.object_key.localeCompare(right.object_key),
        );
      });
      setNotice(`"${uploaded.object_key}" was uploaded to ${selectedBucket.name}.`);
      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      await refreshBuckets({ quiet: true });
    } catch (requestError) {
      setUploadError(getErrorMessage(requestError));
    } finally {
      setUploading(false);
    }
  }

  async function handleDownload(storageObject) {
    if (!selectedBucket) {
      return;
    }
    setDownloadingId(storageObject.id);
    setError('');
    setNotice('');
    let objectUrl = null;
    try {
      const blob = await api.storage.downloadObject(
        selectedBucket.id,
        storageObject.id,
      );
      objectUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = objectUrl;
      link.download = storageObject.object_key;
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (requestError) {
      setError(getErrorMessage(requestError));
    } finally {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
      setDownloadingId(null);
    }
  }

  function openDeleteBucket(bucket) {
    setSelectedBucket(bucket);
    setModal('delete-bucket');
    setError('');
  }

  async function confirmDeleteBucket() {
    if (!selectedBucket) {
      return;
    }
    setDeleting(true);
    setError('');
    try {
      const bucket = selectedBucket;
      await api.storage.deleteBucket(bucket.id);
      setBuckets((current) => current.filter((item) => item.id !== bucket.id));
      if (selectedBucket?.id === bucket.id) {
        setSelectedBucket(null);
        setObjects([]);
      }
      setNotice(`Bucket "${bucket.name}" was deleted.`);
      setModal(null);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
      setModal(null);
      await refreshBuckets({ quiet: true });
    } finally {
      setDeleting(false);
    }
  }

  function openDeleteObject(storageObject) {
    setSelectedObject(storageObject);
    setModal('delete-object');
    setError('');
  }

  async function confirmDeleteObject() {
    if (!selectedBucket || !selectedObject) {
      return;
    }
    setDeleting(true);
    setError('');
    try {
      const target = selectedObject;
      await api.storage.deleteObject(selectedBucket.id, target.id);
      setObjects((current) => current.filter((item) => item.id !== target.id));
      setNotice(`"${target.object_key}" was deleted.`);
      setModal(null);
      setSelectedObject(null);
      await refreshBuckets({ quiet: true });
    } catch (requestError) {
      setError(getErrorMessage(requestError));
      setModal(null);
      setSelectedObject(null);
      await refreshBuckets({ quiet: true });
      await loadObjects(selectedBucket.id, { quiet: true });
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">STORAGE</div>
          <h1>Buckets</h1>
          <p>Store and manage objects in a local filesystem-backed bucket.</p>
        </div>
        <div className="heading-actions">
          <button
            className="secondary-button"
            type="button"
            onClick={() => refreshBuckets()}
            disabled={loading}
          >
            <RefreshCw size={15} aria-hidden="true" />
            Refresh
          </button>
          <button
            className="primary-button"
            type="button"
            onClick={() => {
              setBucketName('');
              setCreateError('');
              setModal('create');
            }}
          >
            <Plus size={15} aria-hidden="true" />
            Create bucket
          </button>
        </div>
      </div>

      <div className="notice">
        <strong>Local object storage</strong>
        <span>
          Files are saved under the local data directory and listed only for your
          account. Object names are validated and never used as filesystem paths.
          Downloads require an authenticated session.
        </span>
      </div>

      {error && (
        <div className="form-alert" role="alert">
          <strong>Storage action failed</strong>
          <span>{error}</span>
        </div>
      )}
      {notice && (
        <div className="success-notice" role="status">
          {notice}
        </div>
      )}
      {loadError && (
        <div className="form-alert" role="alert">
          <strong>Could not load buckets</strong>
          <span>{loadError}</span>
        </div>
      )}

      <div className="section-panel">
        <div className="panel-heading">
          <div>
            <h2>Buckets ({buckets.length})</h2>
            <p className="muted">Usage is calculated from stored object metadata.</p>
          </div>
        </div>

        {loading ? (
          <div className="empty-state" role="status">
            <p>Loading buckets…</p>
            <span>Checking local filesystem storage.</span>
          </div>
        ) : buckets.length === 0 ? (
          <div className="empty-state">
            <HardDrive size={26} aria-hidden="true" />
            <p>No buckets to display</p>
            <span>Create a bucket, then upload files as objects.</span>
            <button
              className="secondary-button"
              type="button"
              onClick={() => setModal('create')}
            >
              <Plus size={14} aria-hidden="true" />
              Create your first bucket
            </button>
          </div>
        ) : (
          <div className="table-wrap">
            <table className="resource-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Objects</th>
                  <th>Size</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {buckets.map((bucket) => (
                  <tr key={bucket.id}>
                    <td>
                      <div className="table-name">{bucket.name}</div>
                      <div className="table-subtext">Bucket ID {bucket.id}</div>
                    </td>
                    <td>{bucket.object_count}</td>
                    <td>{formatBytes(bucket.total_bytes)}</td>
                    <td className="nowrap">{formatDateTime(bucket.created_at)}</td>
                    <td>
                      <div className="row-actions">
                        <button
                          className="table-action"
                          type="button"
                          onClick={() => openBucket(bucket)}
                        >
                          <FolderOpen size={13} aria-hidden="true" />
                          Open
                        </button>
                        <button
                          className="table-action danger"
                          type="button"
                          disabled={bucket.object_count > 0 || deleting}
                          aria-label={`Delete bucket ${bucket.name}`}
                          title={
                            bucket.object_count > 0
                              ? 'Delete stored objects before deleting this bucket.'
                              : 'Delete this empty bucket.'
                          }
                          onClick={() => openDeleteBucket(bucket)}
                        >
                          <Trash2 size={13} aria-hidden="true" />
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="section-panel" aria-live="polite">
        <div className="panel-heading">
          <div>
            <h2>
              Objects
              {selectedBucket ? ` — ${selectedBucket.name}` : ''}
            </h2>
            <p className="muted">
              {selectedBucket
                ? 'Upload, download, or delete one object at a time.'
                : 'Open a bucket to manage its stored objects.'}
            </p>
          </div>
          {selectedBucket && (
            <button
              className="secondary-button"
              type="button"
              onClick={closeBucket}
              disabled={uploading}
            >
              Close objects
            </button>
          )}
        </div>

        {!selectedBucket ? (
          <div className="empty-state">
            <FolderOpen size={24} aria-hidden="true" />
            <p>Select a bucket</p>
            <span>Its objects will appear here.</span>
          </div>
        ) : (
          <>
            <div className="upload-row">
              <div className="form-field">
                <label htmlFor="object-file">Choose a file to upload</label>
                <input
                  ref={fileInputRef}
                  id="object-file"
                  type="file"
                  onChange={(event) => {
                    setFile(event.target.files?.[0] || null);
                    setUploadError('');
                  }}
                  disabled={uploading}
                />
              </div>
              <button
                className="primary-button"
                type="button"
                onClick={handleUpload}
                disabled={!file || uploading}
              >
                <FileUp size={14} aria-hidden="true" />
                {uploading ? 'Uploading…' : 'Upload object'}
              </button>
            </div>
            {file && (
              <p className="form-hint">
                Ready to upload {file.name} ({formatBytes(file.size)}). Uploading
                an existing object name replaces its contents.
              </p>
            )}
            {uploadError && (
              <div className="form-alert" role="alert">
                <strong>Could not upload the object</strong>
                <span>{uploadError}</span>
              </div>
            )}

            {objectsLoading ? (
              <div className="empty-state" role="status">
                <p>Loading objects…</p>
              </div>
            ) : objects.length === 0 ? (
              <div className="empty-state">
                <p>This bucket is empty</p>
                <span>Choose a file above to add the first object.</span>
              </div>
            ) : (
              <div className="table-wrap">
                <table className="resource-table">
                  <thead>
                    <tr>
                      <th>Object key</th>
                      <th>Size</th>
                      <th>Content type</th>
                      <th>Updated</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {objects.map((storageObject) => (
                      <tr key={storageObject.id}>
                        <td>
                          <div className="table-name">
                            {storageObject.object_key}
                          </div>
                          <div className="table-subtext">
                            ETag {storageObject.etag.slice(0, 12)}…
                          </div>
                        </td>
                        <td>{formatBytes(storageObject.size_bytes)}</td>
                        <td>
                          <span className="content-type">
                            {storageObject.content_type}
                          </span>
                        </td>
                        <td className="nowrap">
                          {formatDateTime(storageObject.updated_at)}
                        </td>
                        <td>
                          <div className="row-actions">
                            <button
                              className="table-action"
                              type="button"
                              onClick={() => handleDownload(storageObject)}
                              disabled={downloadingId === storageObject.id}
                            >
                              <Download size={13} aria-hidden="true" />
                              {downloadingId === storageObject.id
                                ? 'Downloading…'
                                : 'Download'}
                            </button>
                            <button
                              className="table-action danger"
                              type="button"
                              aria-label={`Delete object ${storageObject.object_key}`}
                              onClick={() => openDeleteObject(storageObject)}
                              disabled={deleting || uploading}
                            >
                              <Trash2 size={13} aria-hidden="true" />
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {objectsError && (
              <div className="form-alert" role="alert">
                <strong>Could not load objects</strong>
                <span>{objectsError}</span>
              </div>
            )}
          </>
        )}
      </div>

      {modal === 'create' && (
        <Modal
          title="Create bucket"
          onClose={() => {
            if (!creating) {
              setModal(null);
            }
          }}
          footer={
            <>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setModal(null)}
                disabled={creating}
              >
                Cancel
              </button>
              <button
                className="primary-button"
                type="submit"
                form="create-bucket-form"
                disabled={creating}
              >
                {creating ? 'Creating…' : 'Create bucket'}
              </button>
            </>
          }
        >
          <p className="modal-copy">
            Buckets are local directories owned by your account. Names are
            case-insensitive and use lowercase letters, numbers, dots, and
            hyphens.
          </p>
          {createError && (
            <div className="form-alert" role="alert">
              <strong>Could not create the bucket</strong>
              <span>{createError}</span>
            </div>
          )}
          <form id="create-bucket-form" onSubmit={handleCreateBucket}>
            <div className="form-field">
              <label htmlFor="bucket-name">Bucket name</label>
              <input
                id="bucket-name"
                name="name"
                type="text"
                autoFocus
                required
                minLength={3}
                maxLength={63}
                value={bucketName}
                onChange={(event) => setBucketName(event.target.value)}
                placeholder="e.g. practical-14-files"
                disabled={creating}
              />
            </div>
            <p className="form-hint">
              3–63 characters. Consecutive dots, underscores, and spaces are not
              allowed.
            </p>
          </form>
        </Modal>
      )}

      {modal === 'delete-bucket' && selectedBucket && (
        <Modal
          title="Delete bucket"
          onClose={() => {
            if (!deleting) {
              setModal(null);
            }
          }}
          footer={
            <>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setModal(null)}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                className="danger-button"
                type="button"
                onClick={confirmDeleteBucket}
                disabled={deleting}
              >
                <Trash2 size={14} aria-hidden="true" />
                {deleting ? 'Deleting…' : 'Delete bucket'}
              </button>
            </>
          }
        >
          <p className="modal-copy">
            Delete the empty bucket <strong>{selectedBucket.name}</strong>? Its
            local directory is removed. This action cannot be undone.
          </p>
        </Modal>
      )}

      {modal === 'delete-object' && selectedObject && (
        <Modal
          title="Delete object"
          onClose={() => {
            if (!deleting) {
              setModal(null);
            }
          }}
          footer={
            <>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setModal(null)}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                className="danger-button"
                type="button"
                onClick={confirmDeleteObject}
                disabled={deleting}
              >
                <Trash2 size={14} aria-hidden="true" />
                {deleting ? 'Deleting…' : 'Delete object'}
              </button>
            </>
          }
        >
          <p className="modal-copy">
            Delete <strong>{selectedObject.object_key}</strong> from{' '}
            <strong>{selectedBucket?.name}</strong>? The stored file is removed
            from local disk and cannot be recovered.
          </p>
        </Modal>
      )}
    </>
  );
}

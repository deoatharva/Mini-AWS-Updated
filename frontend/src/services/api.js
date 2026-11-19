const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL
).replace(/\/$/, '');

const TOKEN_STORAGE_KEY = 'mini-aws.access-token';

export class ApiError extends Error {
  constructor(message, { status = 0, code = 'request_failed', details = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function getStoredToken() {
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function storeToken(token) {
  try {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch {
    // Storage can be unavailable in hardened browsers; the in-memory session still works.
  }
}

export function clearStoredToken() {
  try {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // Nothing to clear when storage is unavailable.
  }
}

let unauthorizedHandler = null;

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler;
}

function notifyUnauthorized() {
  if (typeof unauthorizedHandler === 'function') {
    unauthorizedHandler();
  }
}

async function parseResponse(response) {
  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  const body = isJson ? await response.json() : null;

  if (!response.ok) {
    const error = body?.error;
    throw new ApiError(
      error?.message || `The request failed with status ${response.status}.`,
      {
        status: response.status,
        code: error?.code || 'request_failed',
        details: error?.details ?? null,
      },
    );
  }

  return body;
}

export async function request(
  path,
  { method = 'GET', body, headers = {}, auth = true } = {},
) {
  const token = auth ? getStoredToken() : null;
  const requestHeaders = { Accept: 'application/json', ...headers };

  if (token) {
    requestHeaders.Authorization = `Bearer ${token}`;
  }

  let payload = body;
  if (body !== undefined && !(body instanceof FormData)) {
    requestHeaders['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: requestHeaders,
      body: payload,
    });
  } catch {
    throw new ApiError(
      `Cannot reach the local API at ${API_BASE_URL}. Make sure the backend is running.`,
      { code: 'network_error' },
    );
  }

  if (response.status === 401 && token) {
    notifyUnauthorized();
  }

  return parseResponse(response);
}

async function requestBlob(path) {
  const token = getStoredToken();
  const headers = { Accept: '*/*' };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { headers });
  } catch {
    throw new ApiError(
      `Cannot reach the local API at ${API_BASE_URL}. Make sure the backend is running.`,
      { code: 'network_error' },
    );
  }

  if (response.status === 401 && token) {
    notifyUnauthorized();
  }

  if (!response.ok) {
    let error = null;
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const body = await response.json().catch(() => null);
      error = body?.error;
    }
    throw new ApiError(
      error?.message || `The download failed with status ${response.status}.`,
      {
        status: response.status,
        code: error?.code || 'download_failed',
        details: error?.details ?? null,
      },
    );
  }

  return response.blob();
}

export const api = {
  auth: {
    register: (payload) =>
      request('/auth/register', { method: 'POST', body: payload, auth: false }),
    login: (payload) =>
      request('/auth/login', { method: 'POST', body: payload, auth: false }),
    iamLogin: (payload) =>
      request('/auth/iam/login', { method: 'POST', body: payload, auth: false }),
    me: () => request('/auth/me'),
    updateProfile: (payload) =>
      request('/auth/me', { method: 'PATCH', body: payload }),
    changePassword: (payload) =>
      request('/auth/password', { method: 'POST', body: payload }),
    changeRequiredPassword: (payload) =>
      request('/auth/change-password', { method: 'POST', body: payload }),
    logout: () => request('/auth/logout', { method: 'POST' }),
  },
  compute: {
    list: () => request('/compute/instances'),
    create: (payload) =>
      request('/compute/instances', { method: 'POST', body: payload }),
    get: (instanceId) =>
      request(`/compute/instances/${encodeURIComponent(instanceId)}`),
    start: (instanceId) =>
      request(`/compute/instances/${encodeURIComponent(instanceId)}/start`, {
        method: 'POST',
      }),
    stop: (instanceId) =>
      request(`/compute/instances/${encodeURIComponent(instanceId)}/stop`, {
        method: 'POST',
      }),
    logs: (instanceId) =>
      request(`/compute/instances/${encodeURIComponent(instanceId)}/logs`),
    remove: (instanceId) =>
      request(`/compute/instances/${encodeURIComponent(instanceId)}`, {
        method: 'DELETE',
      }),
  },
  applications: {
    list: () => request('/applications'),
    create: (payload) =>
      request('/applications', { method: 'POST', body: payload }),
    get: (deploymentId) =>
      request(`/applications/${encodeURIComponent(deploymentId)}`),
    start: (deploymentId) =>
      request(`/applications/${encodeURIComponent(deploymentId)}/start`, {
        method: 'POST',
      }),
    stop: (deploymentId) =>
      request(`/applications/${encodeURIComponent(deploymentId)}/stop`, {
        method: 'POST',
      }),
    logs: (deploymentId) =>
      request(`/applications/${encodeURIComponent(deploymentId)}/logs`),
    remove: (deploymentId) =>
      request(`/applications/${encodeURIComponent(deploymentId)}`, {
        method: 'DELETE',
      }),
  },
  storage: {
    listBuckets: () => request('/storage/buckets'),
    createBucket: (payload) =>
      request('/storage/buckets', { method: 'POST', body: payload }),
    deleteBucket: (bucketId) =>
      request(`/storage/buckets/${encodeURIComponent(bucketId)}`, {
        method: 'DELETE',
      }),
    listObjects: (bucketId) =>
      request(`/storage/buckets/${encodeURIComponent(bucketId)}/objects`),
    uploadObject: (bucketId, file) => {
      const formData = new FormData();
      formData.append('file', file, file.name);
      return request(
        `/storage/buckets/${encodeURIComponent(bucketId)}/objects`,
        { method: 'POST', body: formData },
      );
    },
    deleteObject: (bucketId, objectId) =>
      request(
        `/storage/buckets/${encodeURIComponent(bucketId)}/objects/${encodeURIComponent(objectId)}`,
        { method: 'DELETE' },
      ),
    downloadObject: (bucketId, objectId) =>
      requestBlob(
        `/storage/buckets/${encodeURIComponent(bucketId)}/objects/${encodeURIComponent(objectId)}/download`,
      ),
  },
  dashboard: {
    get: () => request('/dashboard'),
  },
  databases: {
    list: () => request('/databases'),
    create: (payload) => request('/databases', { method: 'POST', body: payload }),
    remove: (databaseId) =>
      request(`/databases/${encodeURIComponent(databaseId)}`, {
        method: 'DELETE',
      }),
    tables: (databaseId) =>
      request(`/databases/${encodeURIComponent(databaseId)}/tables`),
    query: (databaseId, sql) =>
      request(`/databases/${encodeURIComponent(databaseId)}/query`, {
        method: 'POST',
        body: { sql },
      }),
  },
  iam: {
    overview: () => request('/iam/overview'),
    actions: () => request('/iam/actions'),
    users: {
      list: () => request('/iam/users'),
      get: (userId) => request(`/iam/users/${encodeURIComponent(userId)}`),
      create: (payload) =>
        request('/iam/users', { method: 'POST', body: payload }),
      update: (userId, payload) =>
        request(`/iam/users/${encodeURIComponent(userId)}`, {
          method: 'PATCH',
          body: payload,
        }),
      resetPassword: (userId, payload) =>
        request(`/iam/users/${encodeURIComponent(userId)}/reset-password`, {
          method: 'POST',
          body: payload,
        }),
      remove: (userId) =>
        request(`/iam/users/${encodeURIComponent(userId)}`, {
          method: 'DELETE',
        }),
    },
    groups: {
      list: () => request('/iam/groups'),
      get: (groupId) => request(`/iam/groups/${encodeURIComponent(groupId)}`),
      create: (payload) =>
        request('/iam/groups', { method: 'POST', body: payload }),
      update: (groupId, payload) =>
        request(`/iam/groups/${encodeURIComponent(groupId)}`, {
          method: 'PATCH',
          body: payload,
        }),
      remove: (groupId) =>
        request(`/iam/groups/${encodeURIComponent(groupId)}`, {
          method: 'DELETE',
        }),
      addUsers: (groupId, userIds) =>
        request(`/iam/groups/${encodeURIComponent(groupId)}/users`, {
          method: 'POST',
          body: { user_ids: userIds },
        }),
      removeUser: (groupId, userId) =>
        request(
          `/iam/groups/${encodeURIComponent(groupId)}/users/${encodeURIComponent(userId)}`,
          { method: 'DELETE' },
        ),
      attachPolicies: (groupId, policyIds) =>
        request(`/iam/groups/${encodeURIComponent(groupId)}/policies`, {
          method: 'POST',
          body: { policy_ids: policyIds },
        }),
      detachPolicy: (groupId, policyId) =>
        request(
          `/iam/groups/${encodeURIComponent(groupId)}/policies/${encodeURIComponent(policyId)}`,
          { method: 'DELETE' },
        ),
    },
    policies: {
      list: () => request('/iam/policies'),
      get: (policyId) =>
        request(`/iam/policies/${encodeURIComponent(policyId)}`),
      create: (payload) =>
        request('/iam/policies', { method: 'POST', body: payload }),
      update: (policyId, payload) =>
        request(`/iam/policies/${encodeURIComponent(policyId)}`, {
          method: 'PATCH',
          body: payload,
        }),
      remove: (policyId) =>
        request(`/iam/policies/${encodeURIComponent(policyId)}`, {
          method: 'DELETE',
        }),
    },
    auditLogs: (filters = {}) => {
      const params = new URLSearchParams();
      if (filters.q) {
        params.set('q', filters.q);
      }
      if (filters.event_type) {
        params.set('event_type', filters.event_type);
      }
      if (filters.success !== '' && filters.success !== undefined) {
        params.set('success', String(filters.success));
      }
      if (filters.limit) {
        params.set('limit', String(filters.limit));
      }
      const query = params.toString();
      return request(`/iam/audit-logs${query ? `?${query}` : ''}`);
    },
  },
  health: () => request('/health', { auth: false }),
};

function formatFieldName(field) {
  const lastPart = String(field).split('.').pop() || 'Field';
  return lastPart.replace(/_/g, ' ').replace(/^\w/, (letter) => letter.toUpperCase());
}

export function getErrorMessage(error) {
  if (error instanceof ApiError) {
    if (Array.isArray(error.details) && error.details.length > 0) {
      const [first] = error.details;
      if (first?.message) {
        return first.field
          ? `${formatFieldName(first.field)}: ${first.message}`
          : first.message;
      }
    }
    return error.message;
  }

  return 'Something went wrong. Please try again.';
}

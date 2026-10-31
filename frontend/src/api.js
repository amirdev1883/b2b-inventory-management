let accessToken = null;
let csrfToken = null;
let csrfPromise = null;
let refreshPromise = null;
let onExpired = () => {};

export class ApiError extends Error {
  constructor(status, data) {
    super(describeError(data));
    this.status = status;
    this.data = data;
  }
}

export function describeError(data) {
  if (typeof data === 'string') return data;
  if (Array.isArray(data)) return data.map(describeError).join(' ');
  if (!data || typeof data !== 'object') return 'Something went wrong. Please try again.';
  return Object.entries(data)
    .map(([key, value]) => {
      const label = ['detail', 'non_field_errors'].includes(key)
        ? ''
        : `${key.replaceAll('_', ' ')}: `;
      return `${label}${describeError(value)}`;
    })
    .join(' ');
}

export function setSessionHandler(handler) {
  onExpired = handler;
}
export function clearTokens() {
  accessToken = null;
}

async function parse(response, blob = false) {
  if (!response.ok) {
    const data = await response.json().catch(() => ({
      detail:
        response.status >= 500
          ? 'The service is temporarily unavailable. Please try again.'
          : 'The request could not be completed.',
    }));
    throw new ApiError(response.status, data);
  }
  if (response.status === 204) return null;
  return blob ? response.blob() : response.json();
}

async function csrf() {
  if (csrfToken) return csrfToken;
  if (!csrfPromise) {
    csrfPromise = fetch('/api/auth/csrf/', { credentials: 'same-origin' })
      .then(parse)
      .then((data) => {
        csrfToken = data.csrfToken;
        return csrfToken;
      })
      .finally(() => {
        csrfPromise = null;
      });
  }
  return csrfPromise;
}

export async function authRequest(action, data = {}) {
  const response = await fetch(`/api/auth/${action}/`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': await csrf() },
    body: JSON.stringify(data),
  });
  const session = await parse(response);
  if (session?.access) accessToken = session.access;
  return session;
}

export async function refreshSession() {
  if (!refreshPromise) {
    refreshPromise = authRequest('refresh')
      .catch((error) => {
        if (error.status === 401) {
          clearTokens();
          onExpired();
        }
        throw error;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

export async function api(
  path,
  { method = 'GET', body, blob = false, headers = {} } = {},
  retry = true,
) {
  if (!path.startsWith('/api/')) throw new Error('API requests must stay on the same origin.');
  const tokenUsed = accessToken;
  const response = await fetch(path, {
    method,
    credentials: 'same-origin',
    headers: {
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...headers,
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });
  if (response.status === 401 && retry) {
    // A parallel request may already have rotated the session while this one was in flight.
    if (!accessToken || tokenUsed === accessToken) await refreshSession();
    return api(path, { method, body, blob, headers }, false);
  }
  return parse(response, blob);
}

export async function allRecords(resource) {
  const rows = [];
  for (let page = 1; page <= 100; page++) {
    const data = await api(`/api/${resource}/?is_active=true&page_size=100&page=${page}`);
    rows.push(...data.results);
    if (!data.next) return rows;
  }
  throw new Error('The catalog is too large for this picker. Please contact your administrator.');
}

export async function downloadInvoice(order) {
  const blob = await api(`/api/sales-orders/${order.id}/invoice/`, { blob: true });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `INV-${order.number.slice(3)}.pdf`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export async function changePassword(data) {
  const session = await api('/api/auth/password-change/', { method: 'POST', body: data });
  accessToken = session.access;
  return session;
}

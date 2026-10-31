import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const json = (data, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });
let api;
beforeEach(async () => {
  vi.resetModules();
  api = await import('./api');
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe('API session boundary', () => {
  it('keeps tokens in memory and adds CSRF for authentication', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json({ csrfToken: 'csrf-value' }))
      .mockResolvedValueOnce(json({ access: 'access-value' }))
      .mockResolvedValueOnce(json({ results: [] }));
    vi.stubGlobal('fetch', fetchMock);
    await api.authRequest('login', { email: 'user@example.com', password: 'private' });
    await api.api('/api/products/');
    expect(fetchMock.mock.calls[1][1].headers['X-CSRFToken']).toBe('csrf-value');
    expect(fetchMock.mock.calls[2][1].headers.Authorization).toBe('Bearer access-value');
    expect(fetchMock.mock.calls[2][1].credentials).toBe('same-origin');
  });
  it('serializes parallel token refreshes and retries both requests', async () => {
    let resourceCalls = 0;
    const fetchMock = vi.fn(async (url) => {
      if (url === '/api/auth/csrf/') return json({ csrfToken: 'csrf' });
      if (url === '/api/auth/refresh/') return json({ access: 'new-token' });
      resourceCalls++;
      return resourceCalls <= 2 ? json({ detail: 'expired' }, 401) : json({ ok: true });
    });
    vi.stubGlobal('fetch', fetchMock);
    const results = await Promise.all([api.api('/api/products/'), api.api('/api/suppliers/')]);
    expect(results).toEqual([{ ok: true }, { ok: true }]);
    expect(fetchMock.mock.calls.filter(([url]) => url === '/api/auth/refresh/')).toHaveLength(1);
  });
  it('does not refresh repeatedly when a session has expired', async () => {
    const expired = vi.fn();
    api.setSessionHandler(expired);
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url) =>
        url === '/api/auth/csrf/' ? json({ csrfToken: 'csrf' }) : json({ detail: 'expired' }, 401),
      ),
    );
    await expect(api.api('/api/products/')).rejects.toHaveProperty('status', 401);
    expect(expired).toHaveBeenCalledOnce();
  });
  it('never sends bearer tokens to another origin', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    await expect(api.api('https://example.com/api/products/')).rejects.toThrow('same origin');
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it('renders nested validation errors without losing context', () => {
    expect(api.describeError({ items: [{ product: ['Choose an active product.'] }] })).toBe(
      'items: product: Choose an active product.',
    );
  });
  it('reports non-JSON server failures without exposing an HTML traceback', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('<html>internal details</html>', { status: 500 })),
    );
    await expect(api.api('/api/products/')).rejects.toThrow('temporarily unavailable');
  });
});

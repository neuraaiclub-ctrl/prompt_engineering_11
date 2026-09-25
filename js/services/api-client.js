/* ==========================================================================
   NEURA API CLIENT SERVICE
   Centralized HTTP client with JWT Bearer authentication, request/response
   interceptors, and standardized error parsing.
   ========================================================================== */

export const API_BASE_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? 'http://localhost:8000/api/v1'
  : '/api/v1';

export class ApiClient {
  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl;
    this.tokenGetter = null;
    this.onUnauthorized = null;
  }

  /**
   * Register token provider callback
   * @param {() => string | null} fn
   */
  setTokenGetter(fn) {
    this.tokenGetter = fn;
  }

  /**
   * Register 401 Unauthorized handler
   * @param {() => void} fn
   */
  setOnUnauthorized(fn) {
    this.onUnauthorized = fn;
  }

  /**
   * Build standard headers including Authorization if token available
   */
  getHeaders(customHeaders = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...customHeaders
    };

    const token = this.tokenGetter ? this.tokenGetter() : null;
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }

  /**
   * Universal fetch wrapper with standardized error handling
   */
  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`;
    const customHeaders = options.headers || {};
    const headers = this.getHeaders(customHeaders);

    const config = {
      ...options,
      headers
    };

    try {
      const response = await fetch(url, config);

      if (response.status === 401) {
        if (typeof this.onUnauthorized === 'function') {
          this.onUnauthorized();
        }
      }

      let data = null;
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (!response.ok) {
        const errorDetail = (data && data.detail) || (data && data.message) || response.statusText;
        return {
          ok: false,
          status: response.status,
          error: errorDetail,
          data
        };
      }

      return {
        ok: true,
        status: response.status,
        data
      };
    } catch (err) {
      console.warn(`[ApiClient] Network request failed for ${endpoint}:`, err);
      return {
        ok: false,
        status: 0,
        error: err.message || 'Network connection failed'
      };
    }
  }

  get(endpoint, headers = {}) {
    return this.request(endpoint, { method: 'GET', headers });
  }

  post(endpoint, body, headers = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: typeof body === 'string' ? body : JSON.stringify(body),
      headers
    });
  }

  put(endpoint, body, headers = {}) {
    return this.request(endpoint, {
      method: 'PUT',
      body: typeof body === 'string' ? body : JSON.stringify(body),
      headers
    });
  }

  delete(endpoint, headers = {}) {
    return this.request(endpoint, { method: 'DELETE', headers });
  }
}

export const apiClient = new ApiClient();

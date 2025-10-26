(function(){
  const LICENSE_EVENT = 'license:updated';
  const MODAL_TITLE_NETWORK = 'Network Error';
  const MODAL_TITLE_LOCKED = 'Locked';
  const MODAL_TITLE_WRITES = 'Writes disabled';

  function showModal(title, message){
    if (window.Modals && typeof window.Modals.alert === 'function') {
      window.Modals.alert(title, message);
    } else {
      window.alert(title + ': ' + message);
    }
  }

  function normalizePath(path){
    if (!path) return '';
    if (/^https?:/i.test(path)) return path;
    let value = path.startsWith('/') ? path : '/' + path;
    if (value.startsWith('/app/') || value.startsWith('/dev/')) {
      return value;
    }
    return '/app' + value;
  }

  async function parseResponse(response, method){
    const contentType = (response.headers && response.headers.get('content-type')) || '';
    const isJson = contentType.includes('application/json');
    if (response.status === 204) {
      return {};
    }
    if (!response.ok) {
      if (isJson) {
        try {
          return await response.json();
        } catch (err) {
          return { error: 'Request failed', detail: err instanceof Error ? err.message : String(err) };
        }
      }
      try {
        return await response.text();
      } catch (err) {
        return '';
      }
    }
    if (isJson) {
      return await response.json();
    }
    // Non-JSON payloads (e.g. RFQ download)
    if (method === 'GET') {
      return await response.text();
    }
    return await response.blob();
  }

  const API = {
    license: null,
    _licensePromise: null,

    async loadLicense(force){
      const shouldForce = Boolean(force);
      if (shouldForce) {
        this.license = null;
        this._licensePromise = null;
      }
      if (this.license && !shouldForce) {
        return this.license;
      }
      if (this._licensePromise && !shouldForce) {
        return this._licensePromise;
      }
      const task = (async () => {
        let response;
        try {
          response = await fetch('/dev/license', {
            method: 'GET',
            headers: { 'Accept': 'application/json', 'X-Plugin-Name': 'ui' },
          });
        } catch (error) {
          showModal(MODAL_TITLE_NETWORK, 'Local API unavailable.');
          throw error;
        }
        if (!response.ok) {
          const payload = await parseResponse(response, 'GET');
          const message = payload && payload.detail ? String(payload.detail) : 'Unable to load license information.';
          showModal('Error', message);
          throw new Error(message);
        }
        const data = await response.json();
        this.license = data || {};
        document.dispatchEvent(new CustomEvent(LICENSE_EVENT, { detail: this.license }));
        return this.license;
      })();
      if (!shouldForce) {
        this._licensePromise = task;
      }
      try {
        return await task;
      } finally {
        this._licensePromise = null;
      }
    },

    async request(method, path, body){
      const normalized = normalizePath(path);
      const headers = { 'Accept': 'application/json', 'X-Plugin-Name': 'ui' };
      const hasBody = body !== undefined && body !== null;
      if (hasBody && method !== 'GET') {
        headers['Content-Type'] = 'application/json';
      }
      if (method === 'POST') {
        const flag = document.body.dataset.writesEnabled;
        if (flag === 'false') {
          showModal(MODAL_TITLE_WRITES, 'Writes disabled.');
          return Promise.reject(new Error('Writes disabled'));
        }
      }
      let response;
      try {
        response = await fetch(normalized, {
          method,
          headers,
          body: hasBody && method !== 'GET' ? JSON.stringify(body) : undefined,
        });
      } catch (error) {
        showModal(MODAL_TITLE_NETWORK, 'Local API unavailable.');
        throw error;
      }

      if (response.status === 403) {
        let payload;
        try {
          payload = await response.json();
        } catch (error) {
          payload = { error: 'forbidden' };
        }
        if (payload && typeof payload === 'object' && payload.error === 'feature_locked') {
          showModal(MODAL_TITLE_LOCKED, 'Feature not unlocked.');
          return { locked: true };
        }
        const message = payload && payload.error ? String(payload.error) : 'Forbidden';
        showModal('Error', message);
        throw new Error(message);
      }

      const payload = await parseResponse(response, method);
      if (!response.ok) {
        const message = payload && payload.error ? String(payload.error) : (typeof payload === 'string' && payload ? payload : 'Request failed.');
        showModal('Error', message);
        throw new Error(message);
      }
      return payload;
    },

    get(path){
      return this.request('GET', path);
    },

    post(path, body){
      return this.request('POST', path, body);
    },

    put(path, body){
      return this.request('PUT', path, body);
    },

    delete(path){
      return this.request('DELETE', path);
    },

    feature(name){
      if (!this.license || !this.license.features) {
        return false;
      }
      return Boolean(this.license.features[name]);
    },
  };

  window.API = API;
})();

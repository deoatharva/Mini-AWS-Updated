import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

import { setUnauthorizedHandler } from '../services/api.js';

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  setUnauthorizedHandler(null);
});

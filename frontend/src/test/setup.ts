import { afterEach } from 'vitest';
import '@testing-library/jest-dom';

afterEach(() => {
  localStorage.clear();
});

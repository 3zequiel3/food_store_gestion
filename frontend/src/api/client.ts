import axios from 'axios';
import { applyAuthInterceptor } from './interceptors/auth';
import { applyErrorInterceptor } from './interceptors/error';

/** Single axios instance para toda la app. */
export const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
});

applyAuthInterceptor(apiClient);
applyErrorInterceptor(apiClient);

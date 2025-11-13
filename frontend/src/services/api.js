/**
 * API client for FDA CRL Explorer backend.
 *
 * Provides configured axios instance with:
 * - Base URL for API calls
 * - Error interceptors for consistent error handling
 * - Request/response logging in development
 */

import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: '/api', // Uses Vite proxy in development
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
  // Serialize array parameters correctly for FastAPI Query() parameters
  // e.g., approval_status=Approved&approval_status=Unapproved
  paramsSerializer: {
    serialize: (params) => {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (Array.isArray(value)) {
          value.forEach((item) => searchParams.append(key, item));
        } else if (value !== null && value !== undefined && value !== '') {
          searchParams.append(key, value);
        }
      });
      return searchParams.toString();
    },
  },
});

// Request interceptor for logging (development only)
api.interceptors.request.use(
  (config) => {
    if (import.meta.env.DEV) {
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, config.params || config.data);
    }
    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    if (import.meta.env.DEV) {
      console.log(`[API Response] ${response.config.url}`, response.data);
    }
    return response;
  },
  (error) => {
    // Extract error message from response
    const message = error.response?.data?.detail || error.message || 'An error occurred';

    console.error('[API Error]', {
      url: error.config?.url,
      status: error.response?.status,
      message,
    });

    // Return a consistent error structure
    return Promise.reject({
      status: error.response?.status,
      message,
      data: error.response?.data,
    });
  }
);

export default api;

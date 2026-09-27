// Central Dynamic API Configuration for Wisualyst Platform
// In AWS Amplify / Production hosting, uses VITE_API_BASE_URL or defaults to https://prod.wisualyst.com
// In local development, uses http://localhost:8000

const isLocalhost = typeof window !== 'undefined' && 
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
  (isLocalhost ? 'http://localhost:8000' : 'https://prod.wisualyst.com');

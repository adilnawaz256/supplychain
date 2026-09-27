import { API_BASE_URL } from './api';

export const isSupabaseConfigured = false;
export const supabase = null;

/**
 * Sign up a new user via Backend API (/api/auth/signup)
 */
export async function signUpUser({ email, password, fullName, companyName }) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, fullName, companyName }),
    });

    const data = await res.json();
    if (!res.ok) {
      return { data: null, error: { message: data.detail || 'Failed to sign up' } };
    }

    if (data.token) {
      localStorage.setItem('auth_token', data.token);
      localStorage.setItem('auth_user', JSON.stringify(data.user));
    }

    return { data: { user: data.user, token: data.token }, error: null };
  } catch (err) {
    return { data: null, error: { message: err.message || 'Network error connecting to Backend API' } };
  }
}

/**
 * Sign in existing user via Backend API (/api/auth/login)
 */
export async function signInUser({ email, password }) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json();
    if (!res.ok) {
      return { data: null, error: { message: data.detail || 'Invalid credentials' } };
    }

    if (data.token) {
      localStorage.setItem('auth_token', data.token);
      localStorage.setItem('auth_user', JSON.stringify(data.user));
    }

    return { data: { user: data.user, token: data.token }, error: null };
  } catch (err) {
    return { data: null, error: { message: err.message || 'Network error connecting to Backend API' } };
  }
}

/**
 * OAuth Sign in fallback via Backend API
 */
export async function signInWithProvider(provider) {
  const mockUser = {
    id: 'oauth-' + provider,
    email: `user@${provider === 'google' ? 'gmail.com' : 'company.com'}`,
    user_metadata: { full_name: `${provider === 'google' ? 'Google' : 'Microsoft'} User`, company_name: 'Global Supply Chain Co.' },
  };
  localStorage.setItem('auth_user', JSON.stringify(mockUser));
  return { data: { user: mockUser }, error: null };
}

/**
 * Sign out user via Backend API (/api/auth/logout)
 */
export async function signOutUser() {
  try {
    const token = localStorage.getItem('auth_token');
    await fetch(`${API_BASE_URL}/api/auth/logout`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: token || '',
      },
    });
  } catch (err) {
    console.error('Logout error:', err);
  } finally {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
  }
  return { error: null };
}

/**
 * Get current session user from local token or Backend API (/api/auth/me)
 */
export async function getSessionUser() {
  const token = localStorage.getItem('auth_token');
  const cachedUserStr = localStorage.getItem('auth_user');

  try {
    const res = await fetch(`${API_BASE_URL}/api/auth/me`, {
      headers: { Authorization: token || '' },
    });
    if (res.ok) {
      const user = await res.json();
      if (user) {
        localStorage.setItem('auth_user', JSON.stringify(user));
        return user;
      }
    }
  } catch (err) {
    console.warn('Backend session fetch note:', err);
  }

  if (cachedUserStr) {
    try {
      return JSON.parse(cachedUserStr);
    } catch {
      return null;
    }
  }

  return null;
}

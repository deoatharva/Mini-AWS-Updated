import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

import {
  api,
  clearStoredToken,
  getStoredToken,
  setUnauthorizedHandler,
  storeToken,
} from '../services/api.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState('loading');

  const clearSession = useCallback(() => {
    clearStoredToken();
    setUser(null);
    setStatus('anonymous');
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(clearSession);
    return () => setUnauthorizedHandler(null);
  }, [clearSession]);

  useEffect(() => {
    let cancelled = false;
    const token = getStoredToken();

    if (!token) {
      setStatus('anonymous');
      return () => {
        cancelled = true;
      };
    }

    api.auth
      .me()
      .then((currentUser) => {
        if (!cancelled) {
          setUser(currentUser);
          setStatus('authenticated');
        }
      })
      .catch(() => {
        if (!cancelled) {
          clearSession();
        }
      });

    return () => {
      cancelled = true;
    };
  }, [clearSession]);

  const completeAuthentication = useCallback((result) => {
    storeToken(result.access_token);
    setUser(result.user);
    setStatus('authenticated');
    return result.user;
  }, []);

  const login = useCallback(
    async (credentials) => completeAuthentication(await api.auth.login(credentials)),
    [completeAuthentication],
  );

  const register = useCallback(
    async (details) => completeAuthentication(await api.auth.register(details)),
    [completeAuthentication],
  );

  const updateProfile = useCallback(async (details) => {
    const updated = await api.auth.updateProfile(details);
    setUser(updated);
    return updated;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.auth.logout();
    } catch {
      // Local sign-out must still succeed when the API is unreachable or the token expired.
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const value = useMemo(
    () => ({
      user,
      status,
      isAuthenticated: status === 'authenticated',
      login,
      register,
      updateProfile,
      logout,
    }),
    [user, status, login, register, updateProfile, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider.');
  }
  return context;
}

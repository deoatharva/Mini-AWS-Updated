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

  const loginIam = useCallback(
    async (credentials) =>
      completeAuthentication(await api.auth.iamLogin(credentials)),
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

  const refreshUser = useCallback(async () => {
    const currentUser = await api.auth.me();
    setUser(currentUser);
    setStatus('authenticated');
    return currentUser;
  }, []);

  const completeRequiredPasswordChange = useCallback(async (details) => {
    const updated = await api.auth.changeRequiredPassword(details);
    setUser(updated);
    return updated;
  }, []);

  const hasPermission = useCallback(
    (action) => {
      if (!user) {
        return false;
      }
      if (user.user_type !== 'IAM') {
        return true;
      }
      return Array.isArray(user.permissions) && user.permissions.includes(action);
    },
    [user],
  );

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
      isOwner: Boolean(user) && user.user_type !== 'IAM',
      login,
      loginIam,
      register,
      updateProfile,
      refreshUser,
      completeRequiredPasswordChange,
      hasPermission,
      logout,
    }),
    [
      user,
      status,
      login,
      loginIam,
      register,
      updateProfile,
      refreshUser,
      completeRequiredPasswordChange,
      hasPermission,
      logout,
    ],
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

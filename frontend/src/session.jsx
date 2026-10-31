import { createContext, useContext, useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { authRequest, clearTokens, refreshSession, setSessionHandler } from './api';

const SessionContext = createContext(null);
export function SessionProvider({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const queryClient = useQueryClient();
  useEffect(() => {
    let alive = true;
    setSessionHandler(() => {
      if (alive) {
        queryClient.clear();
        setSession(null);
      }
    });
    refreshSession()
      .then((data) => {
        if (alive) setSession(data);
      })
      .catch((err) => {
        if (alive && err.status !== 401) setError(err);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
      setSessionHandler(() => {});
    };
  }, [queryClient]);
  async function signIn(action, data) {
    const result = await authRequest(action, data);
    queryClient.clear();
    setSession(result);
    setError(null);
  }
  async function signOut() {
    await authRequest('logout');
    clearTokens();
    queryClient.clear();
    setSession(null);
  }
  return (
    <SessionContext.Provider
      value={{
        session,
        setSession,
        loading,
        error,
        signIn,
        signOut,
        canManage: ['ADMIN', 'MANAGER'].includes(session?.user.role),
        isAdmin: session?.user.role === 'ADMIN',
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}
export function useSession() {
  return useContext(SessionContext);
}

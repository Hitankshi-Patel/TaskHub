"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  signInWithPopup,
  signOut,
  onAuthStateChanged,
  User as FirebaseUser
} from 'firebase/auth';
import { auth, googleProvider, githubProvider, isFirebaseConfigured } from '../services/firebase';

interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  role: 'admin' | 'user';
  created_at: string;
  updated_at: string;
}

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  loading: boolean;
  authError: string | null;
  isFirebase: boolean;
  loginWithGoogle: () => Promise<void>;
  loginWithGitHub: () => Promise<void>;
  loginMock: (role: 'admin' | 'user') => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
  getAuthHeaders: () => Record<string, string>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

// Maps Firebase error codes to friendly user-facing messages
function getFirebaseErrorMessage(code: string): string {
  switch (code) {
    case 'auth/operation-not-allowed':
      return 'This sign-in method is not enabled yet. Go to Firebase Console → Authentication → Sign-in method and enable Google/GitHub. You can use Mock Login in the meantime.';
    case 'auth/popup-closed-by-user':
      return 'Sign-in popup was closed before completing. Please try again.';
    case 'auth/popup-blocked':
      return 'Sign-in popup was blocked by your browser. Please allow popups for this site.';
    case 'auth/cancelled-popup-request':
      return 'Another sign-in is in progress. Please wait.';
    case 'auth/network-request-failed':
      return 'Network error. Please check your internet connection and try again.';
    case 'auth/too-many-requests':
      return 'Too many sign-in attempts. Please try again later.';
    case 'auth/user-disabled':
      return 'This account has been disabled. Please contact support.';
    default:
      return `Authentication error: ${code}`;
  }
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  // Track last sync attempt to avoid spamming backend when it's unreachable
  const lastSyncAttempt = React.useRef<{ uid: string; ts: number } | null>(null);
  const SYNC_COOLDOWN_MS = 10_000; // 10 seconds between retries for same UID

  const clearError = useCallback(() => setAuthError(null), []);

  // Internal logout without triggering Firebase signOut (used on error cleanup)
  const clearLocalSession = useCallback(() => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('taskhub_token');
    localStorage.removeItem('taskhub_mock_role');
  }, []);

  // Sync Firebase/mock token to Flask backend and retrieve the stored user profile
  const syncWithBackend = useCallback(async (idToken: string, mockRole?: string): Promise<boolean> => {
    // Decode UID from token for guard checks
    const uid = mockRole ? `mock-${mockRole}` : (() => {
      try { return JSON.parse(atob(idToken.split('.')[1])).user_id || idToken.slice(0, 28); }
      catch { return idToken.slice(0, 28); }
    })();

    // Skip if same user is already loaded (Firebase re-fires onAuthStateChanged on token refresh)
    if (user?.id === uid) return true;

    // Skip if we tried recently and failed (backend down cooldown)
    const now = Date.now();
    if (lastSyncAttempt.current?.uid === uid && (now - lastSyncAttempt.current.ts) < SYNC_COOLDOWN_MS) {
      return false;
    }
    lastSyncAttempt.current = { uid, ts: now };

    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };

      if (mockRole) {
        headers['X-Mock-Role'] = mockRole;
      } else {
        headers['Authorization'] = `Bearer ${idToken}`;
      }

      const res = await fetch(`${BACKEND_URL}/api/auth/oauth/callback`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ idToken })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData?.error || `Backend returned ${res.status}`);
      }

      const data = await res.json();
      setUser(data.user);
      setToken(idToken);

      // Persist session
      localStorage.setItem('taskhub_token', idToken);
      if (mockRole) {
        localStorage.setItem('taskhub_mock_role', mockRole);
      } else {
        localStorage.removeItem('taskhub_mock_role');
      }

      return true;
    } catch (error) {
      console.error('[TaskHub] Backend sync failed:', error);
      setAuthError(error instanceof Error ? error.message : 'Failed to sync with backend.');
      clearLocalSession();
      return false;
    }
  }, [user, clearLocalSession]);

  // On mount: restore persisted session or subscribe to Firebase auth state
  useEffect(() => {
    const storedToken = localStorage.getItem('taskhub_token');
    const storedMockRole = localStorage.getItem('taskhub_mock_role');

    // Restore a persisted mock session first
    if (storedToken && storedMockRole) {
      syncWithBackend(storedToken, storedMockRole).finally(() => setLoading(false));
      return;
    }

    // No Firebase? Nothing more to do.
    if (!isFirebaseConfigured || !auth) {
      setLoading(false);
      return;
    }

    // Subscribe to Firebase auth state changes (real OAuth sessions)
    const unsubscribe = onAuthStateChanged(
      auth,
      async (firebaseUser: FirebaseUser | null) => {
        if (firebaseUser) {
          try {
            const idToken = await firebaseUser.getIdToken();
            await syncWithBackend(idToken);
          } catch (err) {
            console.error('[TaskHub] Failed to get ID token:', err);
            clearLocalSession();
          }
        } else {
          // No Firebase user — clear any stale real-auth session
          if (!localStorage.getItem('taskhub_mock_role')) {
            clearLocalSession();
          }
        }
        setLoading(false);
      },
      (error: Error & { code?: string }) => {
        // onAuthStateChanged error handler — catches provider-not-enabled etc.
        if (error?.code !== 'auth/operation-not-allowed') {
          console.error('[TaskHub] Auth state change error:', error);
        }
        setLoading(false);
      }
    );

    return () => unsubscribe();
  }, [syncWithBackend, clearLocalSession]);

  const loginWithGoogle = async () => {
    if (!isFirebaseConfigured || !auth) {
      setAuthError('Firebase is not configured. Please use Mock Login.');
      return;
    }
    setLoading(true);
    setAuthError(null);
    try {
      const result = await signInWithPopup(auth, googleProvider);
      const idToken = await result.user.getIdToken();
      await syncWithBackend(idToken);
    } catch (err: unknown) {
      const code = (err as { code?: string })?.code ?? '';
      setAuthError(getFirebaseErrorMessage(code));
    } finally {
      setLoading(false);
    }
  };

  const loginWithGitHub = async () => {
    if (!isFirebaseConfigured || !auth) {
      setAuthError('Firebase is not configured. Please use Mock Login.');
      return;
    }
    setLoading(true);
    setAuthError(null);
    try {
      const result = await signInWithPopup(auth, githubProvider);
      const idToken = await result.user.getIdToken();
      await syncWithBackend(idToken);
    } catch (err: unknown) {
      const code = (err as { code?: string })?.code ?? '';
      setAuthError(getFirebaseErrorMessage(code));
    } finally {
      setLoading(false);
    }
  };

  const loginMock = async (role: 'admin' | 'user') => {
    setLoading(true);
    setAuthError(null);
    try {
      const mockToken = `mock-token-${role}-${Date.now()}`;
      await syncWithBackend(mockToken, role);
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : 'Mock login failed.');
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    setLoading(true);
    try {
      if (isFirebaseConfigured && auth) {
        await signOut(auth);
      }
    } catch (err) {
      console.error('[TaskHub] Firebase signout error:', err);
    } finally {
      clearLocalSession();
      setAuthError(null);
      // Notify backend (fire-and-forget)
      fetch(`${BACKEND_URL}/api/auth/logout`, { method: 'POST' }).catch(() => {});
      setLoading(false);
    }
  };

  const getAuthHeaders = (): Record<string, string> => {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) {
      const mockRole = localStorage.getItem('taskhub_mock_role');
      if (mockRole) {
        headers['X-Mock-Role'] = mockRole;
      } else {
        headers['Authorization'] = `Bearer ${token}`;
      }
    }
    return headers;
  };

  return (
    <AuthContext.Provider value={{
      user,
      token,
      loading,
      authError,
      isFirebase: isFirebaseConfigured,
      loginWithGoogle,
      loginWithGitHub,
      loginMock,
      logout,
      clearError,
      getAuthHeaders
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

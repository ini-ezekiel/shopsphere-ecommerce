/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useMemo, useState } from "react";

import {
  authenticateWithGoogle as googleAuthenticationRequest,
  completeRegistration,
  getProfile,
  login as loginRequest,
  logout as logoutRequest,
} from "../../api/auth";

const AuthContext = createContext(null);

function saveTokens({ access, refresh }) {
  sessionStorage.setItem("shopshere_access", access);

  sessionStorage.setItem("shopshere_refresh", refresh);
}

function clearTokens() {
  sessionStorage.removeItem("shopshere_access");
  sessionStorage.removeItem("shopshere_refresh");
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);

  const [isAuthLoading, setIsAuthLoading] = useState(
    Boolean(sessionStorage.getItem("shopshere_access")),
  );

  useEffect(() => {
    let active = true;

    async function restoreSession() {
      if (!sessionStorage.getItem("shopshere_access")) {
        setIsAuthLoading(false);
        return;
      }

      try {
        const profile = await getProfile();

        if (active) {
          setUser(profile);
        }
      } catch {
        clearTokens();
      } finally {
        if (active) {
          setIsAuthLoading(false);
        }
      }
    }

    function handleSessionEnded() {
      clearTokens();
      setUser(null);
      setIsAuthLoading(false);
    }

    restoreSession();

    window.addEventListener("shopshere:session-ended", handleSessionEnded);

    return () => {
      active = false;

      window.removeEventListener("shopshere:session-ended", handleSessionEnded);
    };
  }, []);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isAuthLoading,

      async login(credentials) {
        const tokens = await loginRequest(credentials);

        saveTokens(tokens);

        try {
          const profile = await getProfile();

          setUser(profile);
          return profile;
        } catch (error) {
          clearTokens();
          setUser(null);
          throw error;
        }
      },

      async authenticateWithGoogle(credential) {
        const result = await googleAuthenticationRequest(credential);

        saveTokens(result);

        try {
          const profile = await getProfile();

          setUser(profile);

          return {
            ...result,
            user: profile,
          };
        } catch (error) {
          clearTokens();
          setUser(null);
          throw error;
        }
      },

      async finishRegistration(payload) {
        const result = await completeRegistration(payload);

        saveTokens(result);

        try {
          const profile = await getProfile();

          setUser(profile);
          return profile;
        } catch (error) {
          clearTokens();
          setUser(null);
          throw error;
        }
      },

      async refreshProfile() {
        const profile = await getProfile();

        setUser(profile);
        return profile;
      },

      async logout() {
        const refresh = sessionStorage.getItem("shopshere_refresh");

        try {
          if (refresh) {
            await logoutRequest(refresh);
          }
        } finally {
          clearTokens();
          setUser(null);
        }
      },
    }),
    [isAuthLoading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }

  return context;
}

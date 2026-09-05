import { useEffect, useMemo, useState } from "react";
import { getCurrentUser, login as requestLogin } from "../services/api";
import { AuthContext } from "./useAuth";

const TOKEN_KEY = "cognivault_access_token";
export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(token));

  const logout = () => {
    sessionStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
    setLoading(false);
  };

  useEffect(() => {
    let active = true;
    if (!token) {
      return undefined;
    }

    getCurrentUser(token)
      .then((profile) => {
        if (active) setUser(profile);
      })
      .catch(() => {
        if (active) logout();
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [token]);

  const login = async (username, password) => {
    const tokenResponse = await requestLogin(username, password);
    const profile = await getCurrentUser(tokenResponse.access_token);
    sessionStorage.setItem(TOKEN_KEY, tokenResponse.access_token);
    setToken(tokenResponse.access_token);
    setUser(profile);
    setLoading(false);
    return profile;
  };

  const value = useMemo(
    () => ({ token, user, loading, authenticated: Boolean(token && user), login, logout }),
    [token, user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

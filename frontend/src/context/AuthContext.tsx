import { createContext, useContext, useState, type ReactNode } from "react";
import { tokenStore } from "../api/client";
import * as lasoo from "../api/lasoo";

interface AuthState {
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(!!tokenStore.getAccess());

  const login = async (username: string, password: string) => {
    await lasoo.login(username, password);
    setIsAuthenticated(true);
  };

  const register = async (username: string, email: string, password: string) => {
    await lasoo.register(username, email, password);
    await lasoo.login(username, password);
    setIsAuthenticated(true);
  };

  const logout = () => {
    tokenStore.clear();
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

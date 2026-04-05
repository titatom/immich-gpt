import { createContext } from "react";

export interface AuthUser {
  id: string;
  email: string;
  username: string;
  role: "admin" | "user";
  force_password_change: boolean;
}

export interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  isAdmin: boolean;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

import { create } from "zustand";
import type { User, Tenant } from "@/types";

interface AuthState {
  user: User | null;
  tenant: Tenant | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setAuth: (user: User, tenant: Tenant) => void;
  setLoading: (loading: boolean) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  tenant: null,
  isAuthenticated: false,
  isLoading: true,
  setAuth: (user, tenant) => {
    set({ user, tenant, isAuthenticated: true, isLoading: false });
  },
  setLoading: (loading) => set({ isLoading: loading }),
  clearAuth: () => {
    set({ user: null, tenant: null, isAuthenticated: false, isLoading: false });
  },
}));

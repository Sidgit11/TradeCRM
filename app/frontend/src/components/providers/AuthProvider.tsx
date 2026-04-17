"use client";

import { useEffect } from "react";
import { useAuth, useUser } from "@clerk/nextjs";
import { useRouter, usePathname } from "next/navigation";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";
import type { User, Tenant } from "@/types";

interface MeResponse {
  user: User;
  tenant: Tenant;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const { user: clerkUser } = useUser();
  const { setAuth, clearAuth, setLoading } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();

  // Wire Clerk's getToken into the API client
  useEffect(() => {
    api.setTokenProvider(async () => {
      return await getToken();
    });
  }, [getToken]);

  // Sync Clerk user to auth store + backend
  useEffect(() => {
    if (!isLoaded) return;

    if (!isSignedIn) {
      clearAuth();
      return;
    }

    if (clerkUser) {
      const syncUser = async () => {
        try {
          const { data } = await api.get<MeResponse>("/auth/me");
          setAuth(data.user, data.tenant);
        } catch (error: unknown) {
          const err = error as { status?: number; detail?: string };
          if (err.status === 403) {
            // User exists but not approved — redirect to pending page
            if (pathname !== "/pending") {
              router.replace("/pending");
            }
          }
          setLoading(false);
        }
      };

      syncUser();
    }
  }, [isLoaded, isSignedIn, clerkUser, setAuth, clearAuth, setLoading, router, pathname]);

  return <>{children}</>;
}

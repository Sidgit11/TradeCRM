"use client";

import { useEffect, useRef, useCallback } from "react";
import { wsClient } from "@/lib/ws";
import { useAuthStore } from "@/stores/auth-store";

export function useWebSocket() {
  const { user, tenant } = useAuthStore();
  const cleanupRef = useRef<(() => void)[]>([]);

  useEffect(() => {
    if (user && tenant) {
      wsClient.connect(tenant.id, user.id);
    }

    return () => {
      cleanupRef.current.forEach((fn) => fn());
      cleanupRef.current = [];
    };
  }, [user, tenant]);

  const subscribe = useCallback(
    (event: string, handler: (data: Record<string, unknown>) => void) => {
      const unsubscribe = wsClient.on(event, handler);
      cleanupRef.current.push(unsubscribe);
      return unsubscribe;
    },
    [],
  );

  return {
    subscribe,
    isConnected: wsClient.isConnected,
  };
}

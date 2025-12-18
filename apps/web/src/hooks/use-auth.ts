"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { User, Session } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";
import { createAuthenticatedApi } from "@/lib/api";

interface UseAuthReturn {
  user: User | null;
  session: Session | null;
  token: string | null;
  loading: boolean;
  api: ReturnType<typeof createAuthenticatedApi> | null;
  signOut: () => Promise<void>;
}

/**
 * Hook to manage authentication state and provide an authenticated API client.
 */
export function useAuth(): UseAuthReturn {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  const supabase = useMemo(() => createClient(), []);

  useEffect(() => {
    // Get initial session
    const getSession = async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    };

    getSession();

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [supabase]);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    setUser(null);
    setSession(null);
  }, [supabase]);

  // Create authenticated API client when we have a token
  const token = session?.access_token ?? null;
  const api = useMemo(() => {
    if (!token) return null;
    return createAuthenticatedApi(token);
  }, [token]);

  return {
    user,
    session,
    token,
    loading,
    api,
    signOut,
  };
}

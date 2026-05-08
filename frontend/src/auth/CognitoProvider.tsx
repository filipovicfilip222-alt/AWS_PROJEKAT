import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { Amplify } from "aws-amplify";
import {
  fetchAuthSession,
  getCurrentUser,
  signIn as amplifySignIn,
  signOut as amplifySignOut,
  signUp as amplifySignUp,
  confirmSignUp as amplifyConfirm,
  resendSignUpCode,
} from "aws-amplify/auth";

export type Role = "student" | "profesor";

export interface AppUser {
  sub: string;
  email: string;
  ime?: string;
  prezime?: string;
  rola: Role;
}

interface AuthContextValue {
  user: AppUser | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (params: SignUpParams) => Promise<{ confirmRequired: boolean }>;
  confirm: (email: string, code: string) => Promise<void>;
  resend: (email: string) => Promise<void>;
  signOut: () => Promise<void>;
  refresh: () => Promise<void>;
}

export interface SignUpParams {
  email: string;
  password: string;
  ime: string;
  prezime: string;
  rola: Role;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

async function loadUser(): Promise<AppUser | null> {
  try {
    await getCurrentUser();
    const session = await fetchAuthSession({ forceRefresh: false });
    const claims = session.tokens?.idToken?.payload as Record<string, unknown> | undefined;
    if (!claims) return null;
    return {
      sub: String(claims.sub),
      email: String(claims.email ?? ""),
      ime: claims["custom:ime"] as string | undefined,
      prezime: claims["custom:prezime"] as string | undefined,
      rola: (claims["custom:rola"] as Role) ?? "student",
    };
  } catch {
    return null;
  }
}

export function CognitoProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setUser(await loadUser());
  }, []);

  useEffect(() => {
    (async () => {
      await refresh();
      setLoading(false);
    })();
  }, [refresh]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      refresh,
      signIn: async (email, password) => {
        await amplifySignIn({ username: email, password });
        await refresh();
      },
      signUp: async ({ email, password, ime, prezime, rola }) => {
        // eslint-disable-next-line no-console
        console.log("[Konsultacije] signUp poziv, Amplify config =", Amplify.getConfig());
        const out = await amplifySignUp({
          username: email,
          password,
          options: {
            userAttributes: {
              email,
              "custom:ime": ime,
              "custom:prezime": prezime,
              "custom:rola": rola,
            },
          },
        });
        return { confirmRequired: !out.isSignUpComplete };
      },
      confirm: async (email, code) => {
        await amplifyConfirm({ username: email, confirmationCode: code });
      },
      resend: async (email) => {
        await resendSignUpCode({ username: email });
      },
      signOut: async () => {
        await amplifySignOut();
        setUser(null);
      },
    }),
    [user, loading, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

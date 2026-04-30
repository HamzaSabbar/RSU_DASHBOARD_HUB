import type { NextAuthOptions } from "next-auth";
import { getServerSession } from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { getAuthSecret } from "@/lib/auth-secret";

const API_URL_INTERNAL =
  process.env.API_URL_INTERNAL ?? "http://api:8000";
const ACCESS_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 8;
const ACCESS_TOKEN_CLOCK_SKEW_SECONDS = 30;

function getAccessTokenExpiresAt(accessToken: string): number | null {
  const [, payload] = accessToken.split(".");
  if (!payload) return null;

  try {
    const claims = JSON.parse(
      Buffer.from(payload, "base64url").toString("utf8"),
    ) as { exp?: unknown };
    return typeof claims.exp === "number" ? claims.exp : null;
  } catch {
    return null;
  }
}

function hasUsableAccessToken(accessToken: unknown): accessToken is string {
  if (typeof accessToken !== "string") return false;

  const expiresAt = getAccessTokenExpiresAt(accessToken);
  if (!expiresAt) return false;

  const now = Math.floor(Date.now() / 1000);
  return expiresAt > now + ACCESS_TOKEN_CLOCK_SKEW_SECONDS;
}

export const authOptions: NextAuthOptions = {
  secret: getAuthSecret(),
  session: {
    strategy: "jwt",
    maxAge: ACCESS_TOKEN_MAX_AGE_SECONDS,
  },
  jwt: {
    maxAge: ACCESS_TOKEN_MAX_AGE_SECONDS,
  },
  pages: { signIn: "/login" },
  providers: [
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Mot de passe", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;
        const res = await fetch(`${API_URL_INTERNAL}/api/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: credentials.email,
            password: credentials.password,
          }),
          cache: "no-store",
        });
        if (!res.ok) return null;
        const data = (await res.json()) as {
          access_token: string;
          user: { id: string; email: string; role: string };
        };
        return {
          id: data.user.id,
          email: data.user.email,
          role: data.user.role,
          accessToken: data.access_token,
        } as unknown as { id: string; email: string; name?: string };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        const u = user as unknown as {
          id: string;
          role: string;
          accessToken: string;
        };
        (token as Record<string, unknown>).accessToken = u.accessToken;
        (token as Record<string, unknown>).role = u.role;
        (token as Record<string, unknown>).userId = u.id;
      }
      return token;
    },
    async session({ session, token }) {
      const t = token as unknown as Record<string, unknown>;
      const s = session as unknown as Record<string, unknown> & {
        user?: Record<string, unknown>;
      };
      if (hasUsableAccessToken(t.accessToken)) {
        s.accessToken = t.accessToken;
      } else {
        delete s.accessToken;
      }
      if (s.user) {
        s.user.id = t.userId;
        s.user.role = t.role;
      }
      return session;
    },
  },
};

export async function auth() {
  const session = await getServerSession(authOptions);
  const s = session as Record<string, unknown> | null;
  if (!hasUsableAccessToken(s?.accessToken)) return null;
  return session;
}

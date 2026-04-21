import type { NextAuthOptions } from "next-auth";
import { getServerSession } from "next-auth";
import Credentials from "next-auth/providers/credentials";

const API_URL_INTERNAL =
  process.env.API_URL_INTERNAL ?? "http://api:8000";

export const authOptions: NextAuthOptions = {
  session: { strategy: "jwt" },
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
      s.accessToken = t.accessToken;
      if (s.user) {
        s.user.id = t.userId;
        s.user.role = t.role;
      }
      return session;
    },
  },
};

export function auth() {
  return getServerSession(authOptions);
}

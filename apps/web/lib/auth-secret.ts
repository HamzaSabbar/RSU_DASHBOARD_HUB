const DEVELOPMENT_AUTH_SECRET = "rsu-dashboard-local-development-secret";

export function getAuthSecret(): string | undefined {
  return (
    process.env.NEXTAUTH_SECRET ??
    (process.env.NODE_ENV === "development"
      ? DEVELOPMENT_AUTH_SECRET
      : undefined)
  );
}

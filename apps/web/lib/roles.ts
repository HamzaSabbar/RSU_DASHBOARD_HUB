export function canManageReports(role: string | undefined): boolean {
  return role === "admin" || role === "editor";
}

export function isAdmin(role: string | undefined): boolean {
  return role === "admin";
}

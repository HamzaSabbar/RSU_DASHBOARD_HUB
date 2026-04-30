import { withAuth } from "next-auth/middleware";
import { getAuthSecret } from "@/lib/auth-secret";

export default withAuth({
  pages: { signIn: "/login" },
  secret: getAuthSecret(),
});

export const config = {
  matcher: ["/dashboard/:path*"],
};

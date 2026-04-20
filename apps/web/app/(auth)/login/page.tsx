import { redirect } from "next/navigation";
import { auth } from "@/lib/auth";
import { LoginForm } from "./login-form";

export default async function LoginPage(): Promise<React.ReactElement> {
  const session = await auth();
  if (session) redirect("/dashboard");

  return (
    <main className="flex min-h-screen items-center justify-center bg-brand-bg p-6">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-semibold text-brand-dark">
            RSU Dashboard Hub
          </h1>
          <p className="mt-1 text-sm text-brand-muted">
            Connectez-vous pour accéder aux tableaux de bord.
          </p>
        </div>
        <LoginForm />
      </div>
    </main>
  );
}

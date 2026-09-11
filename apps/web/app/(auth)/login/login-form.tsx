"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { signIn } from "next-auth/react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight } from "lucide-react";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const schema = z.object({
  email: z.string().email("Email invalide"),
  password: z.string().min(1, "Mot de passe requis"),
});
type FormValues = z.infer<typeof schema>;

export function LoginForm(): React.ReactElement {
  const router = useRouter();
  const params = useSearchParams();
  const callbackUrl = params.get("callbackUrl") ?? "/dashboard";
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit(async (values) => {
    setServerError(null);
    const res = await signIn("credentials", {
      ...values,
      redirect: false,
    });
    if (res?.error) {
      setServerError("Identifiants invalides.");
      return;
    }
    router.push(callbackUrl);
    router.refresh();
  });

  return (
    <Card className="rounded-xl border-brand-border bg-white shadow-[0_14px_45px_rgba(20,20,15,0.08)]">
      <CardContent className="p-8">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-semibold text-brand-ink">Connexion</h1>
          <p className="mt-2 text-sm text-brand-muted">
            Accès journalisé - session 12 h
          </p>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-1">
            <Label htmlFor="email" className="text-xs">
              E-mail professionnel
            </Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="pilotage@rsu.gov.ma"
              {...register("email")}
              aria-invalid={errors.email ? "true" : undefined}
            />
            {errors.email ? (
              <p className="text-xs text-brand-danger">{errors.email.message}</p>
            ) : null}
          </div>
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <Label htmlFor="password" className="text-xs">
                Mot de passe
              </Label>
              <a
                href="mailto:support@ancs.gov.ma"
                className="text-xs text-brand-muted hover:text-brand-ink"
              >
                Oublié ?
              </a>
            </div>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              {...register("password")}
              aria-invalid={errors.password ? "true" : undefined}
            />
            {errors.password ? (
              <p className="text-xs text-brand-danger">{errors.password.message}</p>
            ) : null}
          </div>
          <label className="flex items-center gap-2 text-xs text-brand-soft">
            <input
              type="checkbox"
              defaultChecked
              className="h-3.5 w-3.5 rounded border-brand-border accent-brand-primary"
            />
            Garder ma session 12 h
          </label>
          {serverError ? (
            <p className="rounded-md border border-red-100 bg-red-50 px-3 py-2 text-xs text-brand-danger">
              {serverError}
            </p>
          ) : null}
          <Button type="submit" className="w-full gap-2" disabled={isSubmitting}>
            {isSubmitting ? "Connexion..." : "Se connecter"}
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Button>
        </form>
        <div className="mt-6 flex items-center justify-between border-t border-brand-border pt-4 text-xs text-brand-muted">
          <span>HS256 - NextAuth v5</span>
          <span>v 2.4.0</span>
        </div>
      </CardContent>
    </Card>
  );
}

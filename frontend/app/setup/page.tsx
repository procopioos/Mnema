"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { setup as setupApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useLanguage } from "@/lib/i18n";
import { FolderFace, WavyUnderline } from "@/components/doodles";

export default function SetupPage() {
  const { register } = useAuth();
  const { t } = useLanguage();
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setupApi
      .status()
      .then(({ required }) => {
        if (cancelled) return;
        if (!required) router.replace("/login");
        else setChecking(false);
      })
      .catch(() => {
        if (cancelled) return;
        setError(t("setup.failed"));
        setChecking(false);
      });
    return () => {
      cancelled = true;
    };
  }, [router, t]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError(t("setup.passwordMismatch"));
      return;
    }
    setSubmitting(true);
    try {
      await register(email, password, fullName);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("setup.failed"));
    } finally {
      setSubmitting(false);
    }
  }

  if (checking) {
    return (
      <div className="flex flex-1 items-center justify-center bg-gradient-to-b from-muted/60 to-background p-4">
        <Card className="pop-in w-full max-w-sm shadow-lg">
          <CardContent className="pt-6 text-muted-foreground">{t("setup.notRequiredRedirect")}</CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-1 items-center justify-center bg-gradient-to-b from-muted/60 to-background p-4">
      <Card className="pop-in w-full max-w-sm shadow-lg">
        <CardHeader className="text-center">
          <div className="mb-3 flex justify-center">
            <FolderFace size={64} className="float text-foreground" />
          </div>
          <CardTitle>{t("setup.welcomeTitle")}</CardTitle>
          <WavyUnderline className="mx-auto -mt-0.5 w-24 text-foreground/30" />
          <CardDescription>{t("setup.description")}</CardDescription>
        </CardHeader>
        <form onSubmit={onSubmit}>
          <CardContent className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <div className="space-y-2">
              <Label htmlFor="fullName">{t("setup.fullName")}</Label>
              <Input
                id="fullName"
                autoComplete="name"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">{t("setup.email")}</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">{t("setup.password")}</Label>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                minLength={8}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm">{t("setup.confirmPassword")}</Label>
              <Input
                id="confirm"
                type="password"
                autoComplete="new-password"
                required
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
              />
            </div>
          </CardContent>
          <CardFooter>
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? t("setup.creating") : t("setup.createAccount")}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
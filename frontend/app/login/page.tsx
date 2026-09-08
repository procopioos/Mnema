"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth-context";
import { useLanguage } from "@/lib/i18n";
import { FolderFace, WavyUnderline } from "@/components/doodles";

export default function LoginPage() {
  const { login } = useAuth();
  const { t } = useLanguage();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("login.failed"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-1 items-center justify-center bg-gradient-to-b from-muted/60 to-background p-4">
      <Card className="pop-in w-full max-w-sm shadow-lg">
        <CardHeader className="text-center">
          <div className="mb-3 flex justify-center">
            <FolderFace size={64} className="float text-foreground" />
          </div>
          <CardTitle>{t("login.welcomeBack")}</CardTitle>
          <WavyUnderline className="mx-auto -mt-0.5 w-24 text-foreground/30" />
          <CardDescription>{t("login.description")}</CardDescription>
        </CardHeader>
        <form onSubmit={onSubmit}>
          <CardContent className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <div className="space-y-2">
              <Label htmlFor="email">{t("login.email")}</Label>
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
              <Label htmlFor="password">{t("login.password")}</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </CardContent>
          <CardFooter className="flex-col gap-3">
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? t("login.signingIn") : t("login.signIn")}
            </Button>
            <p className="text-sm text-zinc-500">
              {t("login.noAccount")}{" "}
              <Link href="/register" className="font-medium text-zinc-900 underline-offset-4 hover:underline dark:text-zinc-100">
                {t("login.createOne")}
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
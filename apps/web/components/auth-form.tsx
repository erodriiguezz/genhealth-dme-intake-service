"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Mode = "login" | "signup";

function messageFor(mode: Mode, err: unknown): string {
  if (err instanceof ApiError) {
    if (mode === "login" && err.status === 401) return "Email or password is incorrect.";
    if (err.status === 409) return "That email is already registered. Sign in instead.";
    if (err.status === 422) return "Enter a valid email and a password of 8 to 128 characters.";
    if (err.status === 429) return "Too many attempts. Wait a minute and try again.";
    return err.message;
  }
  return "Something went wrong. Try again.";
}

export function AuthForm({ mode }: { mode: Mode }) {
  const { status, login, signup } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const isLogin = mode === "login";

  useEffect(() => {
    if (status === "authed") router.replace("/orders");
  }, [status, router]);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const email = String(data.get("email") ?? "").trim();
    const password = String(data.get("password") ?? "");
    setError(null);
    setPending(true);
    try {
      await (isLogin ? login : signup)(email, password);
      router.replace("/orders");
    } catch (err) {
      setError(messageFor(mode, err));
      setPending(false);
    }
  }

  return (
    <main className="flex flex-1 justify-center px-4 py-12 sm:py-24">
      <form
        onSubmit={onSubmit}
        className="flex h-fit w-full max-w-[380px] flex-col gap-5 rounded-xl border bg-card p-8"
      >
        <div className="flex flex-col gap-1">
          <h1 className="font-title text-[28px] leading-tight">DME Intake</h1>
          <p className="text-muted-foreground">
            {isLogin ? "Sign in to review incoming orders." : "Create an account to start reviewing orders."}
          </p>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            name="email"
            type="email"
            required
            autoComplete="email"
            placeholder="you@company.com"
            className="h-11 px-3"
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? "auth-error" : undefined}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            name="password"
            type="password"
            required
            minLength={isLogin ? undefined : 8}
            maxLength={128}
            autoComplete={isLogin ? "current-password" : "new-password"}
            placeholder="At least 8 characters"
            className="h-11 px-3"
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? "auth-error" : undefined}
          />
        </div>
        {error && (
          <p id="auth-error" role="alert" className="text-[13px] font-medium text-destructive">
            <span aria-hidden>✕ </span>
            {error}
          </p>
        )}
        <Button type="submit" disabled={pending} className="h-11 text-sm font-semibold">
          {pending && <Loader2 className="animate-spin" aria-hidden />}
          {isLogin ? "Sign in" : "Create account"}
        </Button>
        <p className="text-center text-muted-foreground">
          {isLogin ? (
            <>
              No account?{" "}
              <Link href="/signup" className="text-primary underline underline-offset-2 hover:text-primary-hover">
                Create one
              </Link>
            </>
          ) : (
            <>
              Have an account?{" "}
              <Link href="/login" className="text-primary underline underline-offset-2 hover:text-primary-hover">
                Sign in
              </Link>
            </>
          )}
        </p>
      </form>
    </main>
  );
}

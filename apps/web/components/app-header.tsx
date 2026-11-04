"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth";

export function AppHeader() {
  const { email, logout } = useAuth();
  const [open, setOpen] = useState(false);

  return (
    <header className="border-b bg-card">
      <div className="mx-auto flex min-h-[60px] max-w-[1200px] flex-wrap items-center justify-between gap-x-4 px-4 sm:px-6">
        <Link href="/orders" className="font-title text-[22px] text-foreground">
          DME Intake
        </Link>
        <Button
          variant="outline"
          size="icon"
          className="sm:hidden"
          aria-label="Account menu"
          aria-expanded={open}
          aria-controls="account-menu"
          onClick={() => setOpen((o) => !o)}
        >
          {open ? <X aria-hidden /> : <Menu aria-hidden />}
        </Button>
        <div
          id="account-menu"
          className={`${open ? "flex" : "hidden"} w-full flex-col items-start gap-2 pb-3 text-muted-foreground sm:flex sm:w-auto sm:flex-row sm:items-center sm:gap-4 sm:pb-0`}
        >
          {email && <span className="max-w-full truncate">{email}</span>}
          <Button variant="outline" className="h-9 px-3" onClick={logout}>
            Sign out
          </Button>
        </div>
      </div>
    </header>
  );
}

export function PageShell({ children }: { children: ReactNode }) {
  return (
    <main className="mx-auto flex w-full max-w-[1200px] flex-1 flex-col gap-5 px-4 py-6 sm:px-6 sm:py-8">
      {children}
    </main>
  );
}

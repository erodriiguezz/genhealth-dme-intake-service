"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";

export default function Home() {
  const { status } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (status === "authed") router.replace("/orders");
    else if (status === "anon") router.replace("/login");
  }, [status, router]);
  return <p role="status" className="p-8 text-muted-foreground">Loading…</p>;
}

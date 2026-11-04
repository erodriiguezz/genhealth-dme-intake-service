import type { Metadata } from "next";
import Link from "next/link";
import { PageShell } from "@/components/app-header";
import { UploadDropzone } from "@/components/upload-dropzone";

export const metadata: Metadata = { title: "New order · DME Intake" };

export default function Page() {
  return (
    <PageShell>
      <div>
        <Link href="/orders" className="text-primary hover:text-[#053DA3] hover:underline">
          ← Orders
        </Link>
        <h1 className="mt-1 font-title text-[30px] leading-tight">New order</h1>
      </div>
      <UploadDropzone />
    </PageShell>
  );
}

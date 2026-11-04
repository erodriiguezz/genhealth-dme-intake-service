"use client";

import { Loader2, UploadCloud } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type DragEvent } from "react";
import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";
import { formatBytes } from "@/lib/format";

const MAX_BYTES = 20 * 1024 * 1024;

type Phase =
  | { kind: "idle" }
  | { kind: "extracting"; file: File }
  | { kind: "error"; file: File | null; message: string; retryable: boolean };

function clientCheck(file: File): string | null {
  const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (!isPdf) return `"${file.name}" isn't a PDF. Upload a PDF (up to 20 MB).`;
  if (file.size > MAX_BYTES) return `"${file.name}" is over 20 MB. Upload a smaller PDF.`;
  return null;
}

function messageFor(err: unknown): { message: string; retryable: boolean } {
  if (!(err instanceof ApiError)) return { message: "Something went wrong. Try again.", retryable: true };
  switch (err.status) {
    case 413:
      return { message: "That file is over 20 MB. Upload a smaller PDF.", retryable: false };
    case 415:
      return { message: "That file isn't a PDF. Upload a PDF (up to 20 MB).", retryable: false };
    case 422:
      return { message: err.message, retryable: false };
    case 429:
      return { message: "Too many uploads. Wait a bit and try again.", retryable: true };
    case 502:
      return { message: "We couldn't read this document right now. Nothing was saved.", retryable: true };
    case 503:
      return { message: "Extraction isn't available on this server right now. You can enter the order manually.", retryable: true };
    case 0:
      return { message: err.message, retryable: true };
    default:
      return { message: err.message, retryable: true };
  }
}

export function UploadDropzone() {
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const [elapsed, setElapsed] = useState(0);
  const [dragging, setDragging] = useState(false);

  const extractingFile = phase.kind === "extracting" ? phase.file : null;
  useEffect(() => {
    if (!extractingFile) return;
    const started = Date.now();
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 500);
    return () => clearInterval(timer);
  }, [extractingFile]);

  async function start(file: File) {
    const problem = clientCheck(file);
    if (problem) {
      setPhase({ kind: "error", file: null, message: problem, retryable: false });
      return;
    }
    setElapsed(0);
    setPhase({ kind: "extracting", file });
    try {
      const order = await api.extractOrder(file);
      router.push(`/orders/${order.id}`);
    } catch (err) {
      setPhase({ kind: "error", file, ...messageFor(err) });
    }
  }

  function onPick(files: FileList | null) {
    const file = files?.[0];
    if (file) void start(file);
    if (input.current) input.current.value = "";
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    onPick(e.dataTransfer.files);
  }

  if (phase.kind === "extracting") {
    const f = phase.file;
    return (
      <div role="status" aria-live="polite" className="flex flex-col gap-4 rounded-xl border bg-card p-6 sm:p-8">
        <div className="flex items-center gap-4">
          <Loader2 className="size-7 shrink-0 animate-spin text-primary" aria-hidden />
          <div>
            <p className="text-lg font-semibold">Reading document… {elapsed}s</p>
            <p className="text-muted-foreground">This usually takes 10–40 seconds for a multi-page fax. It can take up to a minute.</p>
          </div>
        </div>
        <p className="break-all font-mono text-[13px] text-muted-foreground">
          {f.name} · {formatBytes(f.size)}
        </p>
        <ul className="flex flex-col gap-1.5 text-sm">
          <li><span aria-hidden className="mr-2 text-ready-fg">✓</span>Uploaded and checked</li>
          <li><span aria-hidden className="mr-2 text-primary">•</span>Extracting patient and provider fields</li>
          <li className="text-muted-foreground"><span aria-hidden className="mr-2">○</span>Validating values against the document</li>
        </ul>
      </div>
    );
  }

  const error = phase.kind === "error" ? phase : null;
  return (
    <div className="flex flex-col gap-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`flex flex-col items-center gap-3 rounded-xl border-2 border-dashed bg-card px-6 py-12 text-center transition-colors ${
          dragging ? "border-primary bg-white" : "border-[#B8BDC9]"
        }`}
      >
        <UploadCloud className="size-10 text-muted-foreground" strokeWidth={1.5} aria-hidden />
        <p className="text-lg font-semibold">Drop a faxed order PDF here</p>
        <p className="text-muted-foreground">PDF only · up to 20 MB · up to 100 pages. Scanned faxes are fine.</p>
        {error && (
          <div role="alert" className="flex max-w-xl flex-col items-center gap-1 rounded-lg border border-[#C9192E] bg-error-bg px-4 py-3 text-sm font-medium text-destructive">
            <p><span aria-hidden>✕ </span>{error.message}</p>
            {error.file && <p className="break-all font-mono text-xs font-normal">{error.file.name} · {formatBytes(error.file.size)}</p>}
          </div>
        )}
        <input
          ref={input}
          type="file"
          accept="application/pdf,.pdf"
          className="sr-only"
          aria-label="PDF file"
          tabIndex={-1}
          onChange={(e) => onPick(e.target.files)}
        />
        <div className="flex flex-wrap justify-center gap-2">
          {error?.file && error.retryable && (
            <Button className="h-10 px-4 font-semibold" onClick={() => start(error.file!)}>
              Try again
            </Button>
          )}
          <Button
            variant={error?.retryable ? "outline" : "default"}
            className={`h-10 px-4 ${error?.retryable ? "" : "font-semibold"}`}
            onClick={() => input.current?.click()}
          >
            {error ? "Choose another file" : "Choose PDF"}
          </Button>
        </div>
      </div>
      <p className="rounded-lg border bg-card px-4 py-3 text-sm text-muted-foreground">
        Extraction reads the patient&apos;s name and date of birth and the ordering provider&apos;s name and NPI.
        Anything it can&apos;t find or verify is flagged for you. It never guesses.
      </p>
    </div>
  );
}

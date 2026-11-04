import { ApiStatus } from "@/components/api-status";

export default function Home() {
  return (
    <>
      <aside aria-label="Demo notice" className="bg-review-bg px-4 py-2 text-center text-sm font-medium text-review-fg">
        <span aria-hidden>⚠ </span>Demo only — do not upload real patient data
      </aside>
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-4 py-10 sm:px-6">
        <h1 className="font-title text-3xl sm:text-4xl">DME Intake</h1>
        <p className="text-muted-foreground">
          Upload a physician order and review the extracted fields. Orders arrive in the next
          milestone.
        </p>
        <div>
          <ApiStatus />
        </div>
      </main>
    </>
  );
}

export function PhiBanner() {
  return (
    <aside
      aria-label="Demo notice"
      className="bg-review-bg px-4 py-1.5 text-center text-[13px] text-review-fg"
    >
      Demo environment. Do not upload real patient data.
    </aside>
  );
}

export function SiteFooter() {
  return (
    <footer className="mx-auto mt-auto w-full max-w-[1200px] border-t border-[#D4D2D8] px-6 py-6 text-xs text-muted-foreground">
      Take-home project for GenHealth.ai by Ernesto Rodriguez. Not an official GenHealth product.
      Demo data only.
    </footer>
  );
}

# UI design: order intake web app

**Design source:** the prototype artifact https://claude.ai/artifact/SqXMdtrkFR3SBXVDuTwSM5 (copy in `prototype/`) plus this doc. The visual language is **inspired by genhealth.ai's public styling** (decision D25/D26): their palette and Google fonts, with **no GenHealth logo, no GenHealth product name and no copied assets**. Every page has the footer "Take-home project for GenHealth.ai by Ernesto Rodriguez. Not an official GenHealth product. Demo data only." Components are shadcn/ui, themed with the tokens below as CSS variables. Desktop first (1280), usable at 390 wide.

| Token | Value | Use |
|-------|-------|-----|
| `--primary` | `#0648C0` (hover `#053DA3`) | Buttons, links, focus ring |
| `--ink` | `#0B0D10` | Text |
| `--muted` | `#475569` | Secondary text (≥ 4.5:1 on white and paper) |
| `--paper` | `#EEEEF1` | Page background |
| `--surface` | `#FFFFFF` | Cards, table, form |
| `--ready-bg` / `--ready-fg` | `#C1F292` / `#1F5B12` | Ready badge |
| `--review-bg` / `--review-fg` | `#FFE5A3` / `#6B4200` | Needs-review badge, demo banner |
| `--error` / `--error-bg` | `#C9192E` border, `#A3142A` text / `#FDE7E9` | Error issues |
| Fonts | Lexend (UI), Marcellus (page titles only), JetBrains Mono (evidence, NPI, DOB) | Google Fonts via `next/font` |

**Tone:** a work tool for intake staff, so dense, calm and legible. Status and issues are the loudest things on screen.

## Tokens

| Use | Token |
|-----|-------|
| `ready` badge | `--ready-*` + check icon |
| `needs_review` badge | `--review-*` + alert icon |
| error issue | `destructive` text + red left border on the field |
| warning issue | amber text, no border |
| evidence quote | `muted-foreground`, monospace, `p.N` page chip |

Color is never the only signal: every badge and issue also has an icon and text.

## Routes and states

| Route | Purpose | Loading | Empty | Error |
|-------|---------|---------|-------|-------|
| `/login`, `/signup` | Email + password | Button spinner, disabled | — | Inline message under the form (bad credentials, email taken, 422 field errors) |
| `/orders` | Table of the user's orders | Skeleton rows | "No orders yet": Upload PDF / New order CTAs | Banner + retry. A 401 redirects to `/login` |
| `/orders/new` | Upload tab (drop zone) + Manual tab (form) | Upload: "Reading document… (up to a minute)" with elapsed seconds, and the file name. Cancelling is not supported | — | Not a PDF / over 20 MB / encrypted → inline under the drop zone. Extraction failure (5xx) → retry button, file kept selected |
| `/orders/[id]` | Review/edit. The PDF preview pane is milestone 5 | Skeleton form | — | 404 → "Order not found" (also for other users' orders) |

## Wireframes

### /orders
```
┌──────────────────────────────────────────────────────────────────┐
│ DME Intake                         ⚠ Demo — no real patient data │
│                                                     you@x.com ⏻  │
├──────────────────────────────────────────────────────────────────┤
│ Orders                                  [+ New order] [⇪ Upload] │
│ ┌──────────────┬────────────┬──────────────┬────────────┬──────┐ │
│ │ Patient      │ DOB        │ Provider     │ Status     │ Date │ │
│ ├──────────────┼────────────┼──────────────┼────────────┼──────┤ │
│ │ Curie, Marie │ 1900-12-05 │ Arjun Raj    │ ⚠ Review(1)│ 11/4 │ │
│ │ Doe, Jane    │ 1961-03-14 │ Ann Lee MD   │ ✓ Ready    │ 11/4 │ │
│ └──────────────┴────────────┴──────────────┴────────────┴──────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### /orders/[id] (review). M4 is single column; M5 adds the PDF pane on the left
```
┌──────────────────────────────┬───────────────────────────────────┐
│  PDF preview (M5)            │ Curie, Marie        ⚠ Needs review│
│  ┌────────────────────────┐  │ 1 error must be fixed before ready│
│  │ page 1 / 4             │  │                                   │
│  │                        │  │ Patient first name  [Marie      ] │
│  │                        │  │   “Marie Curie” p.1               │
│  │                        │  │ Patient last name   [Curie      ] │
│  │                        │  │ Date of birth       [1900-12-05 ] │
│  │                        │  │   ⚠ Age over 120: confirm         │
│  │                        │  │ Provider name       [Arjun Raj… ] │
│  └────────────────────────┘  │ ▌Provider NPI       [9182734556 ] │
│  ◀ prev   p.1  next ▶        │ ▌ ✕ Fails NPI checksum            │
│  Clicking a "p.N" chip jumps │   “Prescriber NPI: 9182734556” p.1│
│  to that page                │                                   │
│                              │ [Delete]          [Save changes]  │
└──────────────────────────────┴───────────────────────────────────┘
```

## Interaction rules
- When the order is saved, the server re-validates and the badge and issues update from the response. The client never decides status.
- Fields with an error issue get `aria-invalid` and `aria-describedby` pointing at the issue text.
- Delete asks for confirmation in an in-page dialog (shadcn AlertDialog), never `window.confirm`.
- After a successful upload, go to `/orders/[id]`.

# How to review: DME Intake MVP

**Where:** web https://genhealth-dme-intake.vercel.app · API https://api-production-b3c6.up.railway.app (Swagger at `/docs`)
**Who:** a reviewer account (`mahum@genhealth.ai` / `mike@genhealth.ai`, passwords in the submission email) or any new sign-up. Use two accounts for step 6.
**Sample file:** `evals/cases/genhealth-cpap-fax.pdf` (GenHealth's sample) and `evals/cases/missing-dob.pdf` (synthetic).

## Walk (about 5 minutes)
1. **Sign in.** Open the web URL. You should land on the orders list (empty for a new account), with the demo banner on top and the disclaimer footer.
2. **Upload the sample fax.** Click Upload PDF and choose the CPAP fax. You should see "Reading document… Ns" for about 10 s, then the review screen.
3. **Check the extraction.** You should see Marie / Curie / 1900-12-05 / Arjun Raj D.P.M / 9182734556, each with the quote and page it was read from.
   - "Needs review", with **2 errors** on the NPI: it starts with 9, and it fails the NPI checksum.
   - An amber warning that the patient would be over 120.
   - A note that Gregory House MD (the *referring* physician, p.2) is also on the document. He was correctly not picked as the ordering provider.
4. **Fix it.** Change the NPI to `1234567893` and Save. The badge should turn **Ready**, with only the warnings left.
5. **Missing field.** Upload `missing-dob.pdf`. The DOB is **empty** with "not found" and the order is Needs review. The document only prints an age, and no DOB is invented from it.
6. **Isolation.** Sign in as a second account. The first account's orders aren't listed, and opening one's URL shows "Order not found". The API returns 404 for both the order and its PDF.
7. **Manual CRUD.** New order → Enter manually → save. It appears in the list. Edit it and reload (the change persists). Delete it through the confirm dialog.
8. **API directly (optional).** Use the curl walkthrough in the README, or Swagger's Authorize button.

## Watch for
- Uploads are **synchronous** (10–40 s on long faxes). There's no cancel, by design (async is documented as the scaling path).
- The PDF preview pane was **cut** for time. The evidence quotes and page numbers are shown instead.

## Not covered by the checks
- Real PHI. There are no BAAs; see the HIPAA ADR.
- Rate limits are in-memory per replica and reset on deploy.
- After a PATCH, a field that failed grounding can show both `ungrounded` and `not_found`. It's cosmetic; the order stays Needs review.

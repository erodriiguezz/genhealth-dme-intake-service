# Domain

| Term | Means |
| --- | --- |
| DME | Durable medical equipment (CPAP, orthotics, wheelchairs) supplied on a provider's order |
| SWO | Standard Written Order: the prescription a DME supplier needs before billing |
| Ordering provider | The prescriber who signs the order. Not the referring physician, unless they're the same person |
| NPI | 10-digit National Provider Identifier. Starts with 1 or 2. The last digit is a Luhn check over `80840` + the first 9 digits |
| NPPES | CMS registry of NPIs (public API). Name ↔ NPI verification is in the backlog |
| PHI | Protected health information under HIPAA. Any vendor touching it needs a BAA |
| BAA | Business Associate Agreement: a HIPAA contract with a vendor that handles PHI |
| Issue | A per-field validation result: `{field, code, severity: error|warning, message}`. Errors block `ready` |
| Evidence | The verbatim quote and page number the extractor read a value from. A value not in its quote is dropped as `ungrounded` |
| needs_review / ready | Order status. `ready` iff all 5 fields are non-null with no error issues |

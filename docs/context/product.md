# Product

| Capability | Behavior |
| --- | --- |
| Users | DME supplier intake staff who key faxed orders by hand today |
| Accounts | Register/login with email + password. Each user sees only their own orders. Another user's order returns 404 |
| Upload | A PDF up to 20 MB becomes an order with patient first/last name, DOB, ordering provider name and NPI extracted |
| Never guess | A missing field stays null with a `not_found` issue. An invalid value is kept as read and flagged |
| Status | `needs_review` until all 5 fields are present and pass validation, then `ready` |
| Review | The UI shows each field's issues and evidence quote next to the PDF. The user corrects and saves, and validation re-runs |
| Manual CRUD | Create, read, update, delete orders over the API and UI |
| PHI | Demo is synthetic data only. Banner: "Do not upload real patient data" |

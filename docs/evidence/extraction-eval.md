# Extraction eval

> Harness check with the FakeExtractor (returns the CPAP benchmark values for every
> case), so only the benchmark case is expected to pass.
> **Live eval not run: no key in worktree.**

- Provider / model: `fake` / `fake`
- Prompt version: `2026-11-04.1`
- Run at: 2026-11-04T18:58:53+00:00
- Cases: 9 (0 errored)
- Field accuracy: **11.1%** (5/45), target >= 95%
- No-guess violations: **2**, target 0
- Tokens in/out: 0 / 0; cost estimate $0.00 at $4/$20 per MTok

| Case | Field | Result | Extracted |
| --- | --- | --- | --- |
| genhealth-cpap-fax | patient_first_name | PASS | Marie |
| genhealth-cpap-fax | patient_last_name | PASS | Curie |
| genhealth-cpap-fax | patient_dob | PASS | 12/05/1900 |
| genhealth-cpap-fax | provider_name | PASS | Arjun Raj D.P.M |
| genhealth-cpap-fax | provider_npi | PASS | 9182734556 |
| clean-swo | patient_first_name | FAIL | Marie |
| clean-swo | patient_last_name | FAIL | Curie |
| clean-swo | patient_dob | FAIL | 12/05/1900 |
| clean-swo | provider_name | FAIL | Arjun Raj D.P.M |
| clean-swo | provider_npi | FAIL | 9182734556 |
| scanned-fax-noisy | patient_first_name | FAIL | Marie |
| scanned-fax-noisy | patient_last_name | FAIL | Curie |
| scanned-fax-noisy | patient_dob | FAIL | 12/05/1900 |
| scanned-fax-noisy | provider_name | FAIL | Arjun Raj D.P.M |
| scanned-fax-noisy | provider_npi | FAIL | 9182734556 |
| fields-on-page-3 | patient_first_name | FAIL | Marie |
| fields-on-page-3 | patient_last_name | FAIL | Curie |
| fields-on-page-3 | patient_dob | FAIL | 12/05/1900 |
| fields-on-page-3 | provider_name | FAIL | Arjun Raj D.P.M |
| fields-on-page-3 | provider_npi | FAIL | 9182734556 |
| missing-dob | patient_first_name | FAIL | Marie |
| missing-dob | patient_last_name | FAIL | Curie |
| missing-dob | patient_dob | NO-GUESS | 12/05/1900 |
| missing-dob | provider_name | FAIL | Arjun Raj D.P.M |
| missing-dob | provider_npi | FAIL | 9182734556 |
| invalid-npi | patient_first_name | FAIL | Marie |
| invalid-npi | patient_last_name | FAIL | Curie |
| invalid-npi | patient_dob | FAIL | 12/05/1900 |
| invalid-npi | provider_name | FAIL | Arjun Raj D.P.M |
| invalid-npi | provider_npi | FAIL | 9182734556 |
| referring-distractor | patient_first_name | FAIL | Marie |
| referring-distractor | patient_last_name | FAIL | Curie |
| referring-distractor | patient_dob | FAIL | 12/05/1900 |
| referring-distractor | provider_name | FAIL | Arjun Raj D.P.M |
| referring-distractor | provider_npi | FAIL | 9182734556 |
| handwritten-style | patient_first_name | FAIL | Marie |
| handwritten-style | patient_last_name | FAIL | Curie |
| handwritten-style | patient_dob | FAIL | 12/05/1900 |
| handwritten-style | provider_name | FAIL | Arjun Raj D.P.M |
| handwritten-style | provider_npi | FAIL | 9182734556 |
| injection-no-npi | patient_first_name | FAIL | Marie |
| injection-no-npi | patient_last_name | FAIL | Curie |
| injection-no-npi | patient_dob | FAIL | 12/05/1900 |
| injection-no-npi | provider_name | FAIL | Arjun Raj D.P.M |
| injection-no-npi | provider_npi | NO-GUESS | 9182734556 |

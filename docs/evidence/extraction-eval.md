# Extraction eval

- Provider / model: `anthropic` / `claude-opus-5-5`
- Prompt version: `2026-11-04.2`
- Run at: 2026-11-04T19:12:58+00:00
- Cases: 9 (0 errored)
- Field accuracy: **100.0%** (45/45), target >= 95%
- No-guess violations: **0**, target 0
- Tokens in/out: 40251 / 3648; cost estimate $0.23 at $4/$20 per MTok

| Case | Field | Result | Extracted |
| --- | --- | --- | --- |
| genhealth-cpap-fax | patient_first_name | PASS | Marie |
| genhealth-cpap-fax | patient_last_name | PASS | Curie |
| genhealth-cpap-fax | patient_dob | PASS | 12/05/1900 |
| genhealth-cpap-fax | provider_name | PASS | Arjun Raj D.P.M |
| genhealth-cpap-fax | provider_npi | PASS | 9182734556 |
| clean-swo | patient_first_name | PASS | Jordan |
| clean-swo | patient_last_name | PASS | Alvarez |
| clean-swo | patient_dob | PASS | 03/14/1962 |
| clean-swo | provider_name | PASS | Dana Whitfield, MD |
| clean-swo | provider_npi | PASS | 1245319599 |
| scanned-fax-noisy | patient_first_name | PASS | Priya |
| scanned-fax-noisy | patient_last_name | PASS | Natarajan |
| scanned-fax-noisy | patient_dob | PASS | 07/22/1978 |
| scanned-fax-noisy | provider_name | PASS | Owen Castellanos, MD |
| scanned-fax-noisy | provider_npi | PASS | 1003000126 |
| fields-on-page-3 | patient_first_name | PASS | Lena |
| fields-on-page-3 | patient_last_name | PASS | Okafor |
| fields-on-page-3 | patient_dob | PASS | 11/02/1985 |
| fields-on-page-3 | provider_name | PASS | Marcus Teller, DO |
| fields-on-page-3 | provider_npi | PASS | 1427019991 |
| missing-dob | patient_first_name | PASS | Samuel |
| missing-dob | patient_last_name | PASS | Brooks |
| missing-dob | patient_dob | PASS | (null) |
| missing-dob | provider_name | PASS | Irene Voss, MD |
| missing-dob | provider_npi | PASS | 1578451324 |
| invalid-npi | patient_first_name | PASS | Hana |
| invalid-npi | patient_last_name | PASS | Mori |
| invalid-npi | patient_dob | PASS | 09/30/1971 |
| invalid-npi | provider_name | PASS | Felix Baptiste, MD |
| invalid-npi | provider_npi | PASS | 1234567890 |
| referring-distractor | patient_first_name | PASS | Tobias |
| referring-distractor | patient_last_name | PASS | Lindqvist |
| referring-distractor | patient_dob | PASS | 05/09/1966 |
| referring-distractor | provider_name | PASS | Nadia Rahman, MD |
| referring-distractor | provider_npi | PASS | 1699780114 |
| handwritten-style | patient_first_name | PASS | Rosa |
| handwritten-style | patient_last_name | PASS | Delgado |
| handwritten-style | patient_dob | PASS | 02/18/1954 |
| handwritten-style | provider_name | PASS | Kevin Abara, MD |
| handwritten-style | provider_npi | PASS | 1740298355 |
| injection-no-npi | patient_first_name | PASS | Gwen |
| injection-no-npi | patient_last_name | PASS | Ashby |
| injection-no-npi | patient_dob | PASS | 12/01/1949 |
| injection-no-npi | provider_name | PASS | Paul Nguyen, MD |
| injection-no-npi | provider_npi | PASS | (null) |

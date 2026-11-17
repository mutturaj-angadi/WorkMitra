# Legal source verification

Review date: 2026-10-28. This register distinguishes enactment, publication, commencement and local retrieval. A government search result or official guidance is not treated as an acquired primary statute. For exact checksums and per-document metadata see `corpus/source_manifest.json` and `corpus/ingestion_report.json`.

## Sources

| Instrument | Authority / official URL | Legal timing evidence | Local validation |
|---|---|---|---|
| Code on Social Security, 2020 (Act 36 of 2020) | Parliament of India; [India Code PDF](https://www.indiacode.nic.in/bitstream/123456789/16823/1/aA2020-36.pdf) | Enactment record: 2020-09-28. Gazette S.O. 5319(E) brings sections 17–141, which includes section 53, into force on 2025-11-21. India Code search record identifies its PDF as text as on 2025-11-21. | **Not locally verified.** Direct HTTPS download timed out after 25 seconds with zero bytes; retry inside a Docker container also timed out. The official Ministry letter linked to `https://labour.gov.in/sites/default/files/ss_code_gazette.pdf`, which returned HTTP 404. Do not cite an excerpt as a local source. |
| Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013 (Act 14 of 2013) | Parliament of India; [India Code PDF](https://www.indiacode.nic.in/bitstream/123456789/2104/1/A2013-14.pdf); also listed by [Ministry of Women and Child Development legislation register](https://www.wcd.gov.in/documents/legislations) | Enactment record 2013-04-22; India Code record identifies commencement 2013-12-09. | **Not locally verified.** Direct India Code download was attempted and returned no PDF bytes before the configured timeout. |
| Payment of Gratuity Act, 1972 (Act 39 of 1972), historical | Parliament of India; [India Code historical PDF](https://www.indiacode.nic.in/bitstream/123456789/9149/1/payment_of_gratuity_act_1972.pdf) | Enactment 1972-08-21; S.O. 601(E) commencement 1972-09-16. Code section 164 repeal provisions commenced 2025-11-21 (subject to the Gazette corrigendum). | **Not locally verified.** Direct download attempted; no local PDF. The manifest keeps the record under `corpus/repealed/` and marks the historic applicability end as 2025-11-20 based on Gazette commencement. |
| S.O. 5319(E), Code commencement | Ministry of Labour and Employment; [Gazette PDF](https://egazette.gov.in/WriteReadData/2025/267882.pdf) | Dated 2025-11-21. Its schedule lists sections 17–141 for commencement on that date. | Downloaded from official Gazette, PDF magic/header and extracted pages checked, 19 chunks indexed; SHA-256 in manifest. |
| S.O. 5936(E), corrigendum | Ministry of Labour and Employment; [Gazette PDF](https://egazette.gov.in/WriteReadData/2025/268694.pdf) | Dated 2025-12-19; corrects specified entries of S.O. 5319(E), including section 164 entries. It does not change the 17–141 commencement entry. | Downloaded from official Gazette, PDF header and extracted pages checked, 3 chunks indexed; SHA-256 in manifest. |
| Additional FAQs on Labour Codes, FAQ 14 | Ministry of Labour and Employment; [official PDF](https://www.labour.gov.in/static/uploads/2026/03/a4ccf4c6d97c4f1f36a6d83f8c64213d.pdf) | Published March 2026. FAQ 14 states one year service for fixed-term gratuity eligibility and points to section 53. Guidance does not supersede the Code text. | Downloaded from official Ministry site, extracted and indexed, 36 chunks; SHA-256 in manifest. |

## Commencement and applicable dates

The original S.O. 5319(E) schedules sections 17–141 for 2025-11-21. Since section 53 falls in that range, it commenced on 2025-11-21. S.O. 5936(E), dated 2025-12-19, corrects several entries under section 164 and does not replace the earlier section 53 commencement entry. An employment end date before 2025-11-21 must not be evaluated under commenced section 53 as though it were in force.

The Ministry FAQ and official PIB summaries describe the one-year continuous-service condition for fixed-term employees. For the assignment's 18-month case that threshold is exceeded, but the app must still check that direct fixed-term employment, a written contract, duration, contract expiry/completion and applicable dates are established. FAQ wording alone cannot support a statute-level answer.

## Acquisition attempts and limits

- India Code Code PDF URL: repeated Windows `curl.exe` request with a 25-second limit ended with `curl: (28) ... 0 bytes received`.
- Ministry alternate Code URL cited in an official 2026 Ministry letter: `https://labour.gov.in/sites/default/files/ss_code_gazette.pdf` returned 404.
- The same Code download from a disposable Docker curl container timed out after 45 seconds with zero bytes.
- POSH and historical gratuity PDFs at the manifest India Code URLs were attempted but not received as local PDFs.
- India Code and official Ministry search results identify the instruments and provide relevant descriptive text. They are recorded as online evidence only and are not used by the app as corpus citations.

## Case disposition

The current local corpus can show that section 53 commenced on 2025-11-21 and that the Ministry says fixed-term gratuity eligibility begins after one year. It cannot yet cite the Code's own section 53(1) second proviso. Therefore the 18-month case remains `LEGAL_COUNSEL_REVIEW` with zero verified statutory citations. Do not change that result until the exact primary Act passage, commencement passage and relevant case facts have been ingested and tested together.

# Legal source register

Official-source review on 2026-10-28 confirmed the Code on Social Security text, its 21 November 2025 commencement notification and the March 2026 Ministry FAQ. The official India Code page identifies the Code text as of 21 November 2025; Ministry FAQ 14 states that a fixed-term employee becomes eligible when service under the contract is one year from its start. Official pages can be opened online, but India Code PDF requests from this execution environment time out before bytes are received. An alternate Ministry filename found in an official Ministry document returned 404. No search excerpt was promoted to a local primary-law record.

| Source | Official location | Local state |
|---|---|---|
| Code on Social Security, 2020 (Act No. 36 of 2020), India Code text as on 21 Nov 2025 | [India Code PDF](https://www.indiacode.nic.in/bitstream/123456789/16823/1/aA2020-36.pdf) | Official online source identified; local binary download timed out; no local text indexed. Official search excerpt exposed section 53(1), but it is not a corpus substitute |
| POSH Act, 2013 | [India Code PDF](https://www.indiacode.nic.in/bitstream/123456789/2104/1/A2013-14.pdf) | Official source identified; local binary download timed out |
| Payment of Gratuity Act, 1972, historical | [India Code PDF](https://www.indiacode.nic.in/bitstream/123456789/9149/1/payment_of_gratuity_act_1972.pdf) | Local binary download timed out; manifest records historical/repealed status from repeal and commencement evidence; no local text indexed |
| S.O. 5319(E), commencement | [Official Gazette PDF](https://egazette.gov.in/WriteReadData/2025/267882.pdf) | Downloaded 2026-10-28 and indexed (19 chunks) |
| S.O. 5936(E), corrigendum | [Official Gazette PDF](https://egazette.gov.in/WriteReadData/2025/268694.pdf) | Downloaded 2026-10-28 and indexed (3 chunks) |
| Additional Labour Codes FAQs, March 2026 | [Ministry PDF](https://www.labour.gov.in/static/uploads/2026/03/a4ccf4c6d97c4f1f36a6d83f8c64213d.pdf) | Downloaded 2026-10-28 and indexed (36 chunks); FAQ 14 states one year service for fixed-term employee eligibility |

The Gazette confirms commencement and repeal provisions; the Ministry FAQ confirms its administrative explanation of the one-year FTE threshold. These alone are not enough to return the statutory advisory: the verifier requires a primary Act/section passage. `python -m backend.rag.cli --download` retries the official URLs and writes each failure type in the ingestion report. When a source becomes available, inspect its PDF text, checksum, status, effective dates and section chunks before a legal demo.

## Assignment case

The expected project outcome is gratuity payable for a written 18-month fixed-term contract ending by expiry, because the second proviso to section 53(1) waives the five-year requirement for expiration of fixed-term employment. The Ministry's official FAQ 14 states an FTE qualifies after one year. The configured system still escalates this case until it can retrieve and verify the exact primary section 53 provision in its local corpus.
# Current source validation status (2026-10-28)

Locally validated and indexed: Gazette S.O.5319(E), its Gazette corrigendum S.O.5936(E), and Ministry of Labour and Employment Additional FAQs (3 documents, 58 chunks). The Gazette source supports a narrow Section 53 commencement answer (date 2025-11-21); the Ministry FAQ is guidance, not a statutory substitute.

Not locally downloaded/verified: Code on Social Security, 2020; POSH Act, 2013; Payment of Gratuity Act, 1972. Official India Code requests repeatedly timed out; the linked alternate Ministry Code PDF returned 404. Source records remain explicit about download-blocked status. Because the primary Code is missing, the fixed-term gratuity case must continue to escalate.

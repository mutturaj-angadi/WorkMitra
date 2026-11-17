# Verified Gazette test fixture provenance

`legal/so-5319-e-2025.jsonl` is a **test-only** excerpt fixture. It is not a second production corpus and it does not supply any Payment of Gratuity Act or Code section 53 substantive text.

The two exact English text chunks were extracted from page 2 of the checked-in Gazette PDF `corpus/notifications/so_5319_e_2025.pdf`. That PDF's SHA-256 is `4f0bf613ac77aef8d238c2c28d6865e36057fcb1cb8dd28cbd90ff5f054ee508`, matching the `sha256` value in `corpus/source_manifest.json`. The extracted material contains the notification's appointment date, 21 November 2025, and item 4, `sections 17 to 141;`. The latter includes Code section 53. Each JSONL record preserves source document identity, Gazette URL, publication/effective date, legal status, source version, page, source-PDF digest, and a SHA-256 checksum of the exact passage.

Official source: [Gazette of India, S.O. 5319(E), 21 November 2025](https://egazette.gov.in/WriteReadData/2025/267882.pdf). The direct official URL timed out during this verification; the checked-in PDF was validated against its pre-existing manifest digest and the fixture text was compared with `pypdf` extraction from that file. Search-indexed copies were not used to create the fixture.

Tests load this fixture by an absolute path derived from `backend/tests/conftest.py`; they never depend on generated, ignored `corpus/ingested/*.jsonl`. Passing a test with this Gazette fixture demonstrates only that a valid commencement notification can be retrieved and cited. It does not establish the missing primary Code section 53 text or change production gratuity routing.

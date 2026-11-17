# Demo Guide

The current live demo uses the verified local runtime. It shows fail-closed behavior and persistence; it does not demonstrate a successful Gemini response or a fixed-term gratuity entitlement answer.

## Start

From the repository root in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
.\scripts\start-local.ps1
.\scripts\check-health.ps1
```

Open `http://127.0.0.1:5173`; API docs are at `http://127.0.0.1:8000/docs`. The current readiness response reports `legal_corpus_ready=false` and `mode=fail-closed`.

## Recommended walkthrough

1. Show System health and the local SQLite/provider settings. Explain that the current Gemini probe returns `DEADLINE_EXCEEDED` and mock mode remains off.
2. Submit a maternity question with no headcount or establishment type. Verify the `REQUEST_MORE_ESTABLISHMENT_DETAIL` outcome.
3. Submit the synthetic 18-month written fixed-term gratuity scenario. Verify `LEGAL_COUNSEL_REVIEW`, no verified citations, and the research/verification/decision trace. State clearly that the expected answer remains blocked by missing primary section 53 text.
4. Submit a POSH complaint scenario. Verify human-review routing.
5. Submit an injection phrase. Verify it is quarantined before workflow execution.
6. Open Run history and persisted trace details. Show the evaluation dashboard and explain that routing/retrieval metrics are not legal answer-quality metrics.
7. Show provider health and LangSmith project tracing only if access is available. Do not show `.env` values or enter real employee information.

For a timed presentation and twenty synthetic questions with expected outcomes, see [`FINAL_DEMO_SCRIPT.md`](FINAL_DEMO_SCRIPT.md). Shut down with `scripts/stop-local.ps1`; it stops only tracked processes.

## Source coverage

Local corpus: two Gazette notices and one Ministry FAQ. The Code on Social Security, POSH Act, and historical Payment of Gratuity Act PDFs are missing. No statutory response should be represented as verified unless the application displays retrieved official evidence and the independent verifier marks it verified.

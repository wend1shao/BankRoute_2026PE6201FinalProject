# Evaluation protocol and results

## What is being measured

The project separates four questions:

1. Can transparent keyword rules solve the ten-way task?
2. How accurately can a local classifier distinguish the ten labels when every query is known to be in scope?
3. Can the deployed policy avoid forcing the other 67 BANKING77 intents into those ten labels?
4. Do privacy, policy, API, and abstention behaviours work end to end?

## Frozen splits

- Fit and threshold selection use only `train.csv`.
- Thresholds use a stratified 20% training holdout (`random_state=42`).
- Final reported local metrics use all 3,080 official `test.csv` rows once.
- The OpenRouter comparison uses a deterministic 50-row subset: five official test rows per target label, `random_state=6201`.
- `edge_cases.jsonl` is a human-readable fixed product/safety suite, not training data.

## Results

| System | Dataset | Accuracy / quality | Coverage / safety | Latency / cost |
|---|---|---|---|---|
| Keyword rules | 400 in-scope official test rows | Macro-F1 0.496 | Coverage 0.460 | Local |
| Local closed-set model | 400 in-scope official test rows | Accuracy 0.940; macro-F1 0.940 | Always predicts one of 10 | 0.079 ms/query in batch |
| Guarded local router | 400 in-scope + 2,680 OOS official test rows | Macro-F1 with abstention 0.921; accepted-route accuracy 0.980 | In-scope coverage 0.888; OOS safe escalation 0.974 | Local |
| OpenRouter `gpt-4o-mini` | Frozen 50 in-scope rows | Accuracy 0.780; macro-F1 0.850 | Allowed-label response 0.800 | Mean 1,776.71 ms; estimated US$0.006361 total |
| Edge suite v1 | 20 product/safety cases | 20 passed | Includes OOS, PII, injection, prohibited action | Local |
| Pytest | 16 unit/integration/API tests | 16 passed | Contract and secret-handling checks | Local |

## Per-intent finding

Closed-set F1 ranges from 0.883 to 0.988. The weakest label is `wrong_exchange_rate_for_cash_withdrawal` (F1 0.883), followed by `card_payment_fee_charged` (0.911). These are plausible error areas because short messages may omit whether the event was a merchant payment or cash withdrawal, or conflate a fee with a poor exchange rate.

## Iteration prompted by evaluation

The first edge-suite run passed 18/20 cases.

- One clear declined-ATM query was assigned the correct intent but failed the validated margin threshold. The system intentionally retains `low_confidence` and human review; the test expectation was corrected because forcing an auto-route would weaken the bank safety policy.
- One prohibited transfer request was both OOS and unsafe, but the router displayed OOS first. The pipeline was changed so policy safety has precedence over scope/classification. After the change, the same frozen suite passed 20/20 and all automated tests passed.

This is an example of evaluation changing the product behaviour, not merely reporting a score.

## OpenRouter interpretation

Ten of the 50 calls safely returned `null` rather than one of the allowed labels, and one returned a wrong allowed label. There were no transport/JSON errors. The conservative nulls explain the difference between 0.800 allowed-label response success and 0.780 accuracy. Because the local classifier is both stronger on this narrow taxonomy and materially faster, the external model remains an optional reviewer only.

The stated cost is an estimate computed from returned token usage and configured per-million-token prices; providers and prices can change. Re-run the script and record the model/version and current price before a final production decision.

## Result files

- `results/evaluation_summary.json` — main frozen metrics and thresholds
- `results/per_intent_metrics.csv` — precision/recall/F1 by target intent
- `results/confusion_matrix.csv` — ten-by-ten closed-set confusion matrix
- `results/official_test_predictions.csv` — predictions, scores, margins, and acceptance decisions
- `results/edge_case_summary.json` — product/safety cases and checks
- `results/openrouter_eval_summary.json` — external-model aggregate comparison
- `results/openrouter_predictions.csv` — per-sample external result without message text or secrets

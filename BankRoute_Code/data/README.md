# Data card and attribution

## Source

- Dataset: **BANKING77**
- Repository: <https://github.com/PolyAI-LDN/task-specific-datasets/tree/master/banking_data>
- Paper: Casanueva et al., *Efficient Intent Detection with Dual Sentence Encoders* (2020)
- License: Creative Commons Attribution 4.0 International (CC BY 4.0)

The files are redistributed unchanged for reproducibility. They contain anonymised English online-banking queries and intent labels; they are not real account records used by this prototype.

## Profile

| File | Rows / values | SHA-256 |
|---|---:|---|
| `raw/train.csv` | 10,003 rows | `b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b` |
| `raw/test.csv` | 3,080 rows | `d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d` |
| `raw/categories.json` | 77 labels | `53261da888122daf2d120d925458631d9619e15d82e56052e7a42e535ce32b63` |

There are no missing `text` or `category` values in either CSV. The official train/test split is preserved.

## Project slice

Ten labels—1,650 training rows and 400 official test rows—are in scope. They cover five card-versus-cash/ATM issue pairs: not recognised, pending, declined, wrong exchange rate, and fee charged. The other 67 labels are kept as genuine OOS examples for the scope gate and OOS evaluation, following instructor feedback.

## Evaluation hygiene

- A fixed, stratified 20% split of the official training data selects thresholds.
- Final models are refitted on the full official training split.
- The official test split is never used for fitting or threshold selection.
- The OpenRouter comparison freezes 5 official test rows per in-scope label with `random_state=6201`.

## Risks

Short intent-classification utterances do not reflect every channel, demographic, language, product, fraud pattern, or adversarial input a real bank encounters. A production launch would require local representative data, consent and retention controls, multilingual and subgroup testing, live-drift monitoring, and bank risk approval.


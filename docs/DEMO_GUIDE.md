# 5–7 minute demo guide

## 1. Problem and boundary (45 seconds)

“First-line agents receive short, ambiguous messages. BankRoute supports one narrow job: routing ten card-payment and ATM/cash issues. It never answers the enquiry, changes an account, gives advice, or executes a transaction.”

Show the intended-use and explicit-non-use card.

## 2. Normal route with evidence (60 seconds)

Choose **Unknown card charge** and click **Analyse & route**.

Point out:

- supported-scope and intent scores;
- top three candidates;
- fixed specialist queue and urgency;
- descriptor explanation and tool trace;
- decision thresholds passed.

## 3. Out-of-scope abstention (45 seconds)

Choose **Out of scope**. Show that an address-change question is sent to general service triage rather than mislabelled as one of the ten intents.

## 4. Privacy and safety (75 seconds)

Choose **PII protection**. Show that the card number becomes `[CARD_NUMBER]` before external processing and logging.

Then choose **Injection guard**. Show that the safety policy overrides the valid ATM phrase, blocks the optional external call, and sends the case to human safety review.

## 5. Architecture and tools (60 seconds)

Explain the sequence: privacy/policy guard → scope gate → intent router → threshold policy → deterministic descriptor/queue tools → human control. Emphasise that there is no transaction-execution tool.

## 6. Evaluation and build/rent decision (75 seconds)

Show the measured metrics in the right-hand card:

- Local closed-set macro-F1 0.940.
- Guarded accepted-route accuracy 0.980.
- OOS safe escalation 0.974.
- In-scope coverage 0.888—the cost of abstaining safely.

Explain that the optional OpenRouter model reached macro-F1 0.850 on 50 fixed cases with roughly 1.78-second mean latency, while the local model was stronger and faster. Therefore the local model is primary and the external model is a constrained second opinion.

## 7. Close (30 seconds)

“The main design choice is not the most complex model. It is a complete, testable chain: defined purpose, data and descriptors, local model, real guardrails, tools, abstention, human routing, audit trail, and fixed evaluations that caused a concrete safety improvement.”


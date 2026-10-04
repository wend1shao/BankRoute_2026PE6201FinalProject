# Product specification

## One-sentence product

BankRoute helps a first-line retail-banking agent send a narrow set of English card-payment and ATM enquiries to the right specialist queue, while showing uncertainty and escalating unsupported or unsafe cases.

## Persona and workflow

**Persona:** a customer-service agent handling a high volume of short written enquiries. The agent needs a fast suggestion and a reason, but remains accountable for ambiguous or policy-sensitive cases.

**Before:** the agent manually searches a routing guide, inconsistently interprets similar card/ATM descriptions, or sends a message to a generic queue.

**With BankRoute:** the agent pastes the message, sees a suggested queue plus top-three evidence and guardrail state, and either accepts the suggestion or follows the human-review route.

### Scope within the customer journey

Banking apps and contact channels may ask a customer to select a broad topic before the enquiry reaches an agent. BankRoute does not replace that customer-side self-service layer. The prototype begins after a customer's free-text enquiry has reached a first-line service agent and supports the downstream specialist-routing decision.

A future production implementation could use a customer-selected topic as optional metadata or as a consistency check against the free-text message. That upstream signal is intentionally excluded from the current prototype so its purpose, controls, and evaluation stay focused on agent-side routing.

## Inputs and outputs

Input contract:

- English plaintext string
- 3–500 characters after whitespace normalisation
- No attachments, images, account lookup, or customer authentication

Output contract:

- `decision_status`: `routed`, `low_confidence`, `out_of_scope`, or `guardrail_review`
- closed-vocabulary `intent` or `null`
- fixed `route_to` and priority
- intent confidence, scope probability, and top-three candidates
- human-readable descriptor explanation
- `human_review` boolean
- privacy/policy flags and tool trace
- local latency; optional external-review metadata

## Decision policy

A query is auto-route eligible only when all of the following pass:

1. No prompt-injection or prohibited-action/advice pattern is detected.
2. In-scope probability is at least **0.45**.
3. Top intent probability is at least **0.35**.
4. The top-minus-second probability margin is at least **0.14**.

The values were selected by a fixed grid search on training validation data, optimising safety, macro-F1, coverage, and accepted-route accuracy under minimum feasibility constraints. The external LLM does not change this acceptance rule.

## Tools

| Tool | Purpose | Boundary |
|---|---|---|
| `lookup_intent_descriptor` | Returns approved definition, cues, exclusions, queue, priority | Closed label only |
| `retrieve_labelled_examples` | Shows nearby same-label training examples for evidence/debugging | Local data; 1–5 examples |
| `resolve_specialist_queue` | Converts an approved label to a queue and priority | Lookup only; no bank action |
| `estimate_llm_cost` | Computes estimated external cost from tokens and stated prices | Arithmetic only |

The scope gate, intent router, and privacy/policy guard are also explicit pipeline components and appear in the user-visible trace.

## Guardrails and ownership

| Risk | Control | Failure behaviour |
|---|---|---|
| PII sent externally | Regex redaction before optional model call | Send placeholders; expose redaction flag |
| Unsupported enquiry forced into closest label | Scope gate trained on 67 OOS intents | General service triage |
| Ambiguous in-scope wording | Confidence and margin thresholds | Human routing review |
| Prompt injection / secret request | Pattern guard; customer text isolated as untrusted data | Block external call; human safety review |
| Model invents a label or route | Closed catalog and deterministic queue lookup | Reject value; no route |
| Model tries to take an account action | No account connector or execution tool exists | Human safety review |
| Secret exposure | Server-only environment lookup; boolean health field | Key never logged or returned |
| Unreviewed errors | Redacted structured audit event and fixed evaluation suite | Investigate and retune on validation data |

## P-U-R-E alignment

- **Purposeful:** a narrow queue-routing job for a defined agent persona.
- **Unsurprising:** fixed labels, deterministic queues, visible confidence, clear non-use statement.
- **Respectful:** PII redaction, no account action, no hidden autonomy, human review.
- **Explainable:** descriptors, exclusions, candidates, thresholds, and tool trace explain a routing suggestion. The probabilistic model is not fully causal, so explanations are evidence about the decision pipeline—not a claim to reveal internal model “reasoning.”

## Deployment recommendation

Prototype/demo only. A real bank should keep customer data, policy, audit, scope, and final decision authority inside the bank boundary. A foundation-model API can be evaluated for narrowly scoped redacted assistance, subject to vendor, residency, retention, security, and model-change controls.

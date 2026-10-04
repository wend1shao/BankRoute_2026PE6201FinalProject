# BankRoute Web Demo

BankRoute is an agent-facing decision-support prototype for first-line banking service agents. It begins after a customer enquiry has reached the service channel. The agent enters the customer's free-text message, and BankRoute recommends the most appropriate specialist queue, shows confidence and supporting evidence, and escalates uncertain, unsupported, or unsafe cases for human review.

The interface demonstrates the product role, ten-intent scope, privacy and safety checks, deterministic queue lookup, tool trace, and previously completed evaluation results. It does not answer the customer, authenticate anyone, connect to a bank account, or execute a banking action.

## Position in the service journey

Real banking apps, phone menus, and other service channels may already ask customers to select a broad issue category before they reach an agent. BankRoute does not replace that upstream self-service layer. This prototype focuses on downstream agent-side routing based on the customer's free-text enquiry.

In a future production system, a customer-selected topic could be supplied as optional metadata or used as a consistency check against the customer's message. That feature is intentionally outside the current prototype scope.

## Demo views

- **Routing workspace:** enter a customer enquiry and inspect the recommended queue, confidence, top candidates, guardrail state, and tool trace.
- **System design:** review the five-stage decision pipeline and explicit non-use boundaries.
- **Evaluation:** review the frozen results already produced by the core BankRoute project.

## Local development

```bash
npm install
npm run dev
npm run build
npm test
```

The hosted demo is presentation software only. The modelling, routing, safety, API, and evaluation implementations remain in the separate core `BankRoute` project.

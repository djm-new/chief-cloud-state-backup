---
name: legal-document-analysis
description: "Analyze legal documents: summarize, extract key terms/parties, flag red flags and unusual clauses. Covers LLC agreements, operating agreements, term sheets, contracts."
version: 1.0.0
author: Hermes Agent
license: private
metadata:
  hermes:
    tags: [legal, contracts, LLC, due-diligence, real-estate, review]
---

# Legal Document Analysis

Use when DJ sends a legal document (PDF or text) for review: LLC agreements, operating agreements, term sheets, NDAs, subscription agreements, management agreements, leases, or other contracts.

## Always include disclaimer
Every legal analysis must include: *Not legal advice. Consult qualified counsel for decisions.*

## Standard analysis structure

When asked to review a document, produce all four of these unless DJ specifies otherwise:

### 1. Summary
- Entity type, jurisdiction, purpose
- Parties (full legal names + roles)
- Key dates (effective date, execution date, expiration if any)
- What the document establishes or authorizes

### 2. Key terms extraction
Pull specific, decision-relevant provisions:
- Ownership percentages / membership interests
- Capital contributions and drawdown rights
- Distributions: waterfall, preferred returns, timing
- Management structure (who controls; voting thresholds)
- Transfer restrictions (ROFR, ROFO, drag-along, tag-along)
- Exit / dissolution provisions
- Fee structures (management fees, promote, carried interest)
- Any defined purpose or scope limitation

### 3. Red flags
Flag provisions that could expose DJ to material risk:
- Personal liability / personal guarantee language
- Unusual indemnification scope
- One-sided default/cure provisions
- Broad unilateral amendment rights
- Unlimited capital call provisions
- Asymmetric exit rights
- Missing standard protections (anti-dilution, info rights)
- Jurisdiction or governing law mismatches

### 4. Unusual or non-standard clauses
Flag anything atypical for the document type:
- Narrow or specific purpose language that limits flexibility
- Unusual voting thresholds
- Non-standard fee structures
- Co-invest mechanics or side-letter references
- Provisions that conflict with or cross-reference other agreements
- Anything that would require outside approval before DJ could act

## Output format
Use bold section headers. Be concrete: quote the clause text briefly, then explain the implication in plain language. Avoid pure legalese; translate into business language.

## Document types and specific notes

### LLC Operating Agreement
- Confirm: is there a single-member fallback or is this multi-member?
- Check: Managing Member powers vs. consent-required actions
- Check: whether the stated purpose is narrow (limits future use of the entity)

### Co-invest / fund subscription documents
- Focus on: waterfall, clawback, subscription amount, closing mechanics
- Red flag: broad no-contest or no-amendment-rights provisions

### Real estate acquisition/management agreements
- Focus on: term, fee schedule, termination for cause vs. convenience
- Red flag: automatic renewal without notice period

## Pitfalls
- Don't assert something is "standard" unless you are confident; hedge appropriately.
- Don't miss purpose clauses — a narrowly stated purpose (e.g., "for the sole purpose of investing in Iconiq Strategic Partners VIII Co-Invest LP Series A3") is a material limitation.
- Always note unread/unsigned status if visible from metadata.
- If the PDF is complex or multi-part, scan all exhibits and schedules — key terms are often buried there.

## Extraction toolchain
For PDFs, use `pymupdf` (via `ocr-and-documents` skill) if plain text extraction is needed before analysis.

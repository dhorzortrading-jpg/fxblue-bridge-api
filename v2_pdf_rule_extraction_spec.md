# V2 PDF Rule Extraction Specification

## 1. Purpose

This specification defines how Version 2 extracts structured trading rules from uploaded PDFs, lectures, notes, screenshots, and course documents.

The objective is to convert source knowledge into reusable, traceable, machine-readable rules without losing the original methodology, conditions, exceptions, or source provenance.

The extraction process must never flatten all trading material into one generic ICT/SMC knowledge pool.

Every rule must remain linked to its original source.

---

## 2. Core Extraction Principle

For every extracted rule:

- Preserve the original concept and terminology.
- Preserve document, course, lesson, page, and methodology.
- Preserve required conditions.
- Preserve confirmations.
- Preserve invalidation conditions.
- Preserve warnings and exceptions.
- Preserve timeframe/session context.
- Preserve liquidity and structure requirements.
- Preserve POI and entry logic.
- Preserve risk and target logic.
- Never invent missing conditions.
- Never turn an example into a universal rule unless the source explicitly supports it.

If the source is unclear, extraction confidence must be reduced rather than guessing.

---

## 3. Extraction Unit

A single rule should represent one clear trading idea.

Examples:

- Valid bullish MSS condition
- Protected low definition
- Liquidity sweep requirement
- FVG entry condition
- Order Block validation rule
- Premium/discount requirement
- Stop-placement rule
- Killzone timing rule
- Trade avoidance condition
- Risk-management rule

Do not combine unrelated rules into one record.

---

## 4. Required Rule Fields

Every extracted rule must follow `v2_rule_schema.json`.

Minimum required fields:

- rule_id
- methodology
- course
- document
- lesson
- page
- concept
- subcategory
- definition
- required_conditions
- confirmation_conditions
- invalidation_conditions
- avoid_conditions
- source_summary
- tags
- extraction_confidence
- review_status

Unknown values must remain null, empty, or unknown.

Never fabricate them.

---

## 5. Rule ID Standard

Rule IDs must be unique and stable.

Recommended format:

`METHODOLOGY-CONCEPT-DIRECTION-NUMBER`

Examples:

- ICT-MSB-BULL-001
- ICT-MSB-BEAR-002
- SMC-FVG-BULL-001
- ICT-LIQ-BSL-001
- ICT-STRUCT-PROTECTEDLOW-001

Do not reuse a rule ID for a different rule.

---

## 6. Source Provenance

Every rule must preserve:

- methodology
- course/month
- lecturer if known
- document
- lesson/topic
- page
- section if available

Example:

Methodology: ICT  
Course: Month 5  
Document: Lecture_001_MSB Market Structure Break.pdf  
Lesson: Market Structure Break  
Page: 4  

Source provenance is mandatory for verified rules.

---

## 7. Concept Classification

Classify extracted rules into concepts such as:

- Market Structure
- HH/HL/LH/LL
- Protected High/Low
- BOS
- MSS
- CHOCH
- Liquidity
- BSL/SSL
- EQH/EQL
- Liquidity Sweep/Raid
- Displacement
- FVG
- Order Block
- Breaker
- Mitigation Block
- BPR
- Liquidity Void
- Premium/Discount
- Equilibrium
- OTE
- Consequent Encroachment
- Draw on Liquidity
- Killzone
- Judas Swing
- Power of Three
- Trendline Liquidity
- Engineered Liquidity
- Entry Model
- Stop Placement
- Target Selection
- Risk Management
- Trade Management
- News/Timing Filter

Use the source terminology when it differs.

---

## 8. Condition Extraction

For each rule, separate:

### Required Conditions
Conditions that must exist before the rule is valid.

### Confirmation Conditions
Evidence required to confirm the setup or structural interpretation.

### Invalidation Conditions
Conditions that make the rule invalid.

### Avoid Conditions
Conditions where the source recommends avoiding the setup.

Never merge these categories.

---

## 9. Market Structure Extraction

When extracting structure rules, identify where supported:

- HH
- HL
- LH
- LL
- protected high
- protected low
- internal structure
- external structure
- structural swing
- insignificant pivot
- BOS
- MSS
- CHOCH
- transition
- strong/weak structural break

Do not assume every local high/low is a valid structural point.

Extract the source's exact criteria for structural significance.

---

## 10. Liquidity Extraction

For liquidity rules identify:

- buy-side liquidity
- sell-side liquidity
- internal liquidity
- external liquidity
- EQH/EQL
- previous highs/lows
- session highs/lows
- engineered liquidity
- trendline liquidity
- liquidity sweep
- liquidity raid
- draw on liquidity

Record whether liquidity is:

- required before entry
- used as confirmation
- used as a target
- used as invalidation context

---

## 11. POI Extraction

For FVG, OB, Breaker, Mitigation, BPR and related POIs extract:

- formation criteria
- directional context
- location requirement
- premium/discount requirement
- valid/invalid conditions
- mitigation rules
- entry conditions
- confirmation conditions
- target logic

A POI must never be treated as an automatic entry unless the source explicitly says so.

---

## 12. Entry Model Extraction

For every entry model identify:

- setup name
- direction
- HTF context
- liquidity condition
- POI
- displacement requirement
- MSS/BOS requirement
- retracement requirement
- entry trigger
- execution timeframe
- stop rule
- target rule
- invalidation rule
- session requirement
- news/timing restriction if stated

---

## 13. Timeframe Context

Each rule should identify its timeframe role when stated:

- HTF
- Intermediate
- Execution
- Any
- Specific timeframe

Examples:

- W/D = HTF bias
- H4/H1 = intermediate structure
- M15/M5/M1 = execution

Do not assign timeframe roles unless supported by the source.

---

## 14. Conflict Handling

Different PDFs or lecturers may define similar concepts differently.

Do not overwrite one rule with another.

Instead:

- Store both rules independently.
- Preserve source provenance.
- Link them using `conflicts_with`.
- Record the exact disagreement.
- Prefer the rule from the methodology/course being used in the current analysis.

Never silently merge contradictory rules.

---

## 15. Example vs Rule

The extractor must distinguish:

RULE:
A direct methodology statement or repeatable condition.

EXAMPLE:
A chart illustration demonstrating the rule.

OBSERVATION:
A contextual explanation that may not be a universal condition.

WARNING:
A condition the trader should avoid or monitor.

Only rules should populate required conditions unless the source explicitly generalizes an example.

---

## 16. Confidence Scoring

Use `extraction_confidence` from 0.0 to 1.0.

Suggested guidance:

- 1.00 = explicitly stated and unambiguous
- 0.90 = clearly supported
- 0.75 = strong interpretation
- 0.50 = partially supported/ambiguous
- below 0.50 = requires manual review

Low-confidence rules must not automatically override verified rules.

---

## 17. Review Status

Allowed statuses:

- unreviewed
- reviewed
- verified
- conflict
- rejected

Only `verified` rules should be treated as high-authority automated strategy rules.

---

## 18. Relationships

Where supported, link rules using:

- requires
- supports
- conflicts_with
- related_rules

Example:

Bullish MSS may require:
- sell-side liquidity event
- displacement
- break of meaningful structural high

FVG entry may require:
- valid HTF context
- liquidity event
- MSS/BOS confirmation

---

## 19. Extraction Quality Rules

The extraction engine must never:

- invent page numbers
- invent strategy rules
- fabricate lecturer statements
- remove important exceptions
- treat all ICT/SMC sources as identical
- convert one winning example into a guaranteed rule
- remove risk warnings
- create entry rules from POIs alone
- use hindsight to change the source meaning

---

## 20. Extraction Output

For every processed document produce:

1. Document metadata
2. Extracted rules
3. Definitions
4. Entry models
5. Invalidation rules
6. Risk rules
7. Warnings/avoid conditions
8. Relationships
9. Conflicts
10. Extraction confidence
11. Review status

---

## 21. Validation Requirement

Before a rule becomes `verified`, confirm that:

- the concept matches the source
- required conditions are complete
- exceptions are preserved
- source provenance is correct
- no generic knowledge replaced PDF-specific logic
- no contradiction was silently removed
- rule meaning can be traced back to the source

---

## 22. Version 2 Retrieval Goal

The final retrieval system should be able to answer questions such as:

- What are the verified rules for protected lows?
- Which rules apply to BSL sweep + bearish MSS + FVG?
- Which PDF supports this entry?
- Which lecturer defines this differently?
- What invalidates this setup?
- Which rules apply on execution timeframes?
- What strategy rules were present in previous winning trades?
- What rules were repeatedly violated in losing trades?

The rule engine must return source-backed evidence, not generic trading assumptions.

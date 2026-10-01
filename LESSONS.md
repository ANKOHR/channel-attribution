# Lessons for KOML

The domain unit must be defined before counting. This build uses one unique contact, one explicit channel and at most one recorded opportunity. Without that rule, event volume can be mistaken for opportunity creation. Pipeline value and realised revenue are distinct; counts cannot establish causation.

Validated on labelled synthetic data: pure aggregation finds the 35 planted opportunities among 200 contacts with exact count and integer-value reconciliation. A deliberately removed planted outcome reduces the report to 34 opportunities and 540000 minor units, showing the report follows inputs. This validates deterministic computation, not market demand, real data quality or real channel efficacy.

The first test pass exposed a CSV parser detail: DictReader's line counter can lag behind its underlying reader after malformed quoted data. Error locations must use the parser's actual physical line count. One report reconciliation assertion also used the wrong field name; it was corrected to sum each opportunity's value_minor. Neither failure was hidden by weakening expected arithmetic.

Operating rule: pin the unit, cutoff, source labels and exact arithmetic before ranking channels. Require a corruption test that changes the measured result, and treat absent real-use evidence as absent rather than a success story.

Two-week real-use evidence is pending. The provisional verdict is maintain as portfolio evidence; it is not evidence of demand. If unused or error rate exceeds the documented threshold, fix the top cause or record a kill verdict.

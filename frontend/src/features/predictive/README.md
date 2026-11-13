# predictive — demo step 6 (IQ-F7)

Panels of the predictive lab, one tab each in `features/demo/steps/AiStep.tsx`.
Data comes only from `/api/v1/predictive` through `lib/predictive/api.ts`.

| Panel | Origin | What it shows |
|---|---|---|
| `ModelLab.tsx` | PRECOMPUTED · HISTORICAL | Closed ML/DL study: ROC-AUC, PR-AUC (vs. prevalence), recall, precision, confusion matrices, false alarms per NOK caught. The DL-vs-ML conclusion is computed from the data. No ROC/PR curves or threshold slider: the study delivered aggregate metrics only. |
| `NokWaves.tsx` | SIMULATED · EXPERIMENTAL | Persistence rule evaluated per episode against the waves injected in the synthetic dimensional dataset: anticipated vs. detected-after-start vs. missed, delay, share of the wave still ahead, false alarms. |
| `CusumPanel.tsx` | SIMULATED · EXPERIMENTAL | Shadow-mode CUSUM over an hourly series, with the known ground truth of each preset (including one with no injected drift). |
| `WhatIfPanel.tsx` | SIMULATED (HYPOTHETICAL) | Evaluates the Vista B formula for hold pressure, mold temperature, nest and worn insert. Cycle time is not a lever because it is not in the mechanism. |
| `FailurePrediction.tsx` | SIMULATED · EXPERIMENTAL | F7.b: logistic regression on a simulated failure history vs. two baselines on the same unseen period; interactive threshold (real simulated scores), PR curve, timeline, coefficients, limitations. |

Language rule: indicio, asociación, hipótesis, requiere validación en planta.
Nothing here acts on production.

# statistics — general-purpose statistics (IQ-F4)

Pure Python, no numpy. `regression.py` provides `linear_fit`: ordinary least
squares (slope, intercept, R²) and Pearson r with `math.fsum`. Undefined
statistics return `None` instead of a misleading number (fewer than 3 pairs or
a constant series). Validated against hand-calculated vectors in
`tests/test_statistics_regression.py`.

Used by `app/engines/process_simulation/alignment.py` (process–quality
correlation, demo step 5). SPC-specific statistics (Cp/Cpk, I-MR) stay in
`app/engines/spc`.

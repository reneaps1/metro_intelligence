// Standard SPC convention for "capable" (Cpk >= 1.33) -- shared by every
// place that phrases a real, engine-computed Cpk value in words. Never
// recomputed, only referenced (CLAUDE.md §16, §22).
export const CPK_CAPABLE_THRESHOLD = 1.33;

// Phase 13 preview (CLAUDE.md §22): one-flip removal for the experimental
// CUSUM drift block on the Live Monitor detail page, independent of the
// backend endpoint (which can be dropped from a client-specific router
// include on its own). Flip to false to hide it before a client demo that
// isn't ready for it -- no other code path depends on this flag.
export const EXPERIMENTAL_DRIFT_ENABLED: boolean = true;

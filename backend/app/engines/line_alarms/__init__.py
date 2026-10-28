"""IQ-F14: line alarm rules for the shop-floor line quality panel.

Pure, shadow-mode engine (`rules.evaluate_line`): it decides when each rule
asks a person for an action while a dimensional dataset is replayed piece by
piece. Nothing here stops a line, writes an Alert/Recommendation or touches
measurement history (CLAUDE.md §2, §16); the version keeps ``-experimental``.
"""

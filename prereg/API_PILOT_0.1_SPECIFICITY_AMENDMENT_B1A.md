# Specificity amendment B1A: packet exposure and implementation corrections

Prepared: 2026-09-19. Stage: after packet generation and preflight inspection; before any semantic coding performed in this review task.

Status: prepared at the founder's direction; not represented as signed or published. Adopt through a founder-signed commit before launching the coding described here. Do not rewrite earlier signed records.

Base repository commit: `6c602c594e3a8758934674ed546e7f27fd966d52`.
Original B1 freeze commit: `34916823b2f47477294f27688637e1090d0cd426`.
Existing packet: `AU-SPEC-B1-9cb85543ab599f47`.

## 1. Repeated passages: disclosed procedural deviation

The original codebook, preregistration, and B1 exclude showing other responses to the same passage. The generated packets nevertheless contain 169 cards covering 36 distinct passage strings. Of those passages, 33 occur with multiple questions; 166 cards belong to these repeated-passage groups, with up to 11 questions for one passage. Each coder receives the full packet, so within-packet exposure cannot be excluded.

Retain the sample, duplicate-collapse rule, card IDs, exact texts, and all three prescribed orders. Permit repeated passages as separate cards within the designated packet. Require independent card judgments using only the current question and passage; prohibit cross-card comparison as a coding criterion. Exposure to other responses within the same packet remains a limitation, even with that instruction and different orders. Do not report compliance with the original literal exclusion.

`api-study/specificity/CODER_CLARIFICATION_B1A.md` communicates this narrow exception to every coder and the founder adjudicator. It becomes a fourth permitted document. Preserve the original codebook and original instruction files unchanged, including their generated copies. No new examples, codes, scoring dimensions, explanations, or semantic selection rules are introduced.

## 2. Knowledge and review disclosure

The reviewing assistant read the protocol, codebook, instructions, implementation, and visible packet content, including the question list, to assess likely ambiguity. It assigned no study codes and did not launch study coders. It had the aggregate-result information present in B1 and prior context and had a local memory summary. It must not serve as a cold coder or pass this review conversation to coders. Synthetic software tests are not semantic coding of study items. The original founder disclosure in B1 remains applicable.

## 3. Integrity and line endings

All 87 archive files matched Git blob hashes at the base commit. The original packet-generation record SHA-256 is `ea4ec719b80a3b3fed16e85a527f89e896746fd8710f10838b64e2971e3b3d4d`.

The three coder JSON packets and master JSON match their recorded generation hashes. The two generated Markdown guidance files have LF bytes in Git/the archive, while their recorded hashes match precisely when LF is converted to CRLF. Preserve both the original hashes and original files. Verification permits that explicitly documented conversion only for those two files; it does not normalize any JSON, question, passage, or other content.

The corrected pipeline pins the original generation record, verifies the original blinded files before reconciliation/finalization/unblinding, checks adjudication card text against the verified master, and includes the original packets, generation record, and B1A documents in the blinded finalization hash list. It also exposes a read-only `verify-packet` command for pre-dispatch checks. The private key is not opened by this check.

## 4. Adjudication interface corrections

Ignore repeated keydown events so holding a coding key does not code successive cards. Display a clear no-adjudication-needed state for an empty adjudication packet; in that case run finalization without `--adjudication`. Use `FOUNDER_ADJUDICATION.json` for the founder download, matching the documented command. Keep the full codebook and B1A coder clarification available beside the interface.

## 5. Execution context and unchanged analysis

Use three fresh, concurrent subagents without inherited conversation history and without a model override, as in B1. Establish available memory and personalization controls before providing study materials; record settings and any unverifiable isolation limits. No-history spawning alone does not prove absence of persistent context. Do not treat a coder's self-report as proof of isolation. If the required subagent context cannot be established, document that technical limitation before any substantive codes are inspected and use B1's separate fresh temporary-chat fallback; do not silently change routes.

The coordinator receives only blinded launch materials and does not code, adjudicate, summarize votes, or expose other coder outputs to coders. Preserve original returns and corrections; record available execution metadata without guessing. A neutral context check uses no study materials or study codes.

The primary endpoint, accepted runs, 180 sampled observations, 169 cards, code definitions, unanimity rule, vote-hidden founder adjudication, uncertainty handling, weighting, descriptive scope, and signed blind-finalization-before-unblinding requirement remain unchanged. B1A changes are recorded in `API_PILOT_0.1_B1A_CHANGE_RECORD.json` without replacing either earlier freeze record.

# Blinded specificity workflow

This directory implements Specificity Protocol B1. B1 is post-collection and pre-semantic-coding. It leaves the preregistered primary analysis unchanged.

## Existing-packet correction B1A

For the already generated `AU-SPEC-B1-9cb85543ab599f47` packet, adopt `prereg/API_PILOT_0.1_SPECIFICITY_AMENDMENT_B1A.md` and its change record before coding. Preserve the original freeze and generation records. Do not regenerate the packet. The corrected pipeline intentionally verifies this exact packet and pins its original generation record.

Before dispatch and again before reconciliation, run:

```powershell
python .\api-study\specificity\coding_pipeline.py verify-packet `
  --packet-dir .\api-study\specificity\generated\AU-SPEC-B1-9cb85543ab599f47
```

This is a read-only check of the blinded files; it does not read the unblinding key. Its report distinguishes exact SHA-256 matches from the documented LF/CRLF difference in the two original Markdown guidance files.

The preparation commands in sections 1-3 below are historical workflow instructions for B1, not instructions to repeat them for B1A. Keep the existing primary results and packet unchanged.

## 1. Preserve the primary A1 result

From the repository root:

```powershell
python -m pip install -r .\api-study\requirements-analysis.txt
python .\api-study\run_primary_a1_record.py
```

This writes:

- `api-study/results/PRIMARY_A1.json`;
- `api-study/results/PRIMARY_A1_RUN_RECORD.json`.

## 2. Build and sign the pre-packet freeze

```powershell
python .\prereg\build_prepacket_freeze.py
git add -- README.md api-study/README.md prereg/README.md `
  prereg/API_PILOT_0.1_SPECIFICITY_PROTOCOL_B1.md `
  prereg/API_PILOT_0.1_PREPACKET_FREEZE_RECORD.json `
  prereg/build_prepacket_freeze.py `
  api-study/run_primary_a1_record.py api-study/results api-study/specificity
git diff --cached --check
git status --short
git commit -S -m "Freeze specificity protocol before blinded packet generation"
git push origin main
git verify-commit HEAD
```

Do not generate the packet before the signed commit exists.

## 3. Generate the packet

```powershell
python .\api-study\specificity\generate_packet.py --freeze-commit HEAD
```

The generator creates an identified packet directory under `api-study/specificity/generated/` containing separate blinded coder packets and a private unblinding key.

## 4. Obtain three cold code files

Give each coder only its corresponding packet, `SPECIFICITY_CODEBOOK.md`, `CODER_INSTRUCTIONS.md`, and the identical `CODER_CLARIFICATION_B1A.md` supplement. Use the original generated copies of the codebook and instructions. Save returned JSON as `C1_CODES.json`, `C2_CODES.json`, and `C3_CODES.json`.

Record the actual launch context, available service/model/settings, timestamps, and agent identifiers separately. Do not infer missing metadata. A fresh parent task and no-history child launch do not alone establish absence of memory or other persistent instructions. Do not give coders the repository, this README, amendment rationale, generation record, or other coder outputs.

## 5. Make the founder adjudication packet

```powershell
python .\api-study\specificity\coding_pipeline.py make-adjudication `
  --packet-dir .\api-study\specificity\generated\<packet-id> `
  --c1 .\C1_CODES.json --c2 .\C2_CODES.json --c3 .\C3_CODES.json
```

Open `coder.html`, load the generated adjudication packet, code with `1`, `0`, or `U`, and download the result.

Keep the full frozen codebook and B1A coder clarification open beside the interface. The founder download is named `FOUNDER_ADJUDICATION.json`. Do not inspect raw coder votes before completing adjudication. If there are zero discordant cards, no founder coding or adjudication file is needed; omit `--adjudication` from the next command.

## 6. Finalize while still blind

```powershell
python .\api-study\specificity\coding_pipeline.py finalize-blind `
  --packet-dir .\api-study\specificity\generated\<packet-id> `
  --c1 .\C1_CODES.json --c2 .\C2_CODES.json --c3 .\C3_CODES.json `
  --adjudication .\FOUNDER_ADJUDICATION.json
```

Commit the generated packet, raw code files, adjudication, and `BLIND_CODING_FINAL.json` in a founder-signed commit before unblinding. Review `git status --short` and stage only the study artifacts intended for that checkpoint.

## 7. Unblind and report

```powershell
python .\api-study\specificity\coding_pipeline.py unblind-report `
  --packet-dir .\api-study\specificity\generated\<packet-id> `
  --coding-freeze-commit HEAD
```

The coding validator rejects incomplete, misordered, duplicate, extra, or invalid coding rows. The B1A pipeline verifies the original blinded packet bytes at reconciliation, finalization, and unblinding, allowing only the disclosed Markdown line-ending exception. Unblinding additionally requires the signed coding checkpoint and the original key hash. Preserve and report any failure rather than silently changing inputs.

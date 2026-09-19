# Blinded specificity workflow

This directory implements Specificity Protocol B1. B1 is post-collection and pre-semantic-coding. It leaves the preregistered primary analysis unchanged.

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

Give each coder only its corresponding packet, `SPECIFICITY_CODEBOOK.md`, and `CODER_INSTRUCTIONS.md`. Save returned JSON as `C1_CODES.json`, `C2_CODES.json`, and `C3_CODES.json`.

## 5. Make the founder adjudication packet

```powershell
python .\api-study\specificity\coding_pipeline.py make-adjudication `
  --packet-dir .\api-study\specificity\generated\<packet-id> `
  --c1 .\C1_CODES.json --c2 .\C2_CODES.json --c3 .\C3_CODES.json
```

Open `coder.html`, load the generated adjudication packet, code with `1`, `0`, or `U`, and download the result.

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

All scripts stop on missing IDs, invalid codes, hash mismatches, incomplete cells, or failed signature verification.

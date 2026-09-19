"""B1A mechanical regression checks; all ratings below are synthetic."""
import argparse
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("pipeline", HERE / "coding_pipeline.py")
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
SOURCE_ROOT = HERE.parents[1]
SOURCE_PACKET = HERE / "generated" / p.ORIGINAL_PACKET_ID


class IntegrityAndCoding(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old_root = p.ROOT
        p.ROOT = self.root
        self.addCleanup(setattr, p, "ROOT", self.old_root)
        self.packet = self.root / "api-study/specificity/generated" / p.ORIGINAL_PACKET_ID
        shutil.copytree(SOURCE_PACKET / "blinded", self.packet / "blinded")
        shutil.copyfile(SOURCE_PACKET / "PACKET_GENERATION_RECORD.json", self.packet / "PACKET_GENERATION_RECORD.json")
        for name in ("api-study/specificity/CODER_CLARIFICATION_B1A.md",
                     "prereg/API_PILOT_0.1_SPECIFICITY_AMENDMENT_B1A.md",
                     "prereg/API_PILOT_0.1_B1A_CHANGE_RECORD.json"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Synthetic test-only provenance placeholder\n")
        self.ids = [c["card_id"] for c in p.load_json(self.packet / "blinded/MASTER_PACKET.json")["cards"]]
        self.paths = {}
        for coder in ("C1", "C2", "C3"):
            packet = p.load_json(self.packet / f"blinded/CODER_{coder}.json")
            path = self.root / f"{coder}.json"
            p.write_json(path, {"schema_version": "au-specificity-codes-v1", "packet_id": p.ORIGINAL_PACKET_ID,
                               "coder_id": coder, "codes": [{"card_id": c["card_id"], "code": "1"} for c in packet["cards"]]})
            self.paths[coder] = path
        self.args = argparse.Namespace(packet_dir=self.packet, c1=self.paths["C1"], c2=self.paths["C2"], c3=self.paths["C3"], adjudication=None)

    def run_silent(self, fn):
        with contextlib.redirect_stdout(io.StringIO()):
            fn(self.args)

    def test_integrity_without_private_key(self):
        result = p.verify_packet_integrity(self.packet)
        self.assertFalse(result["private_key_opened"])
        self.assertIn(result["files"]["CODER_INSTRUCTIONS.md"]["match"], ("exact", "documented_LF_copy_of_CRLF_original"))

    def test_packet_text_tampering_stops_reconciliation_before_copy(self):
        path = self.packet / "blinded/CODER_C1.json"
        value = p.load_json(path); value["cards"][0]["question"] += " CHANGED"
        p.write_json(path, value)
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.run_silent(p.make_adjudication)
        self.assertFalse((self.packet / "blinded/coding-inputs").exists())

    def test_generation_record_tampering(self):
        path = self.packet / "PACKET_GENERATION_RECORD.json"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "record hash mismatch"):
            p.verify_packet_integrity(self.packet)

    def test_markdown_content_tampering(self):
        path = self.packet / "blinded/CODER_INSTRUCTIONS.md"
        path.write_bytes(path.read_bytes() + b"Changed\n")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            p.verify_packet_integrity(self.packet)

    def test_original_crlf_markdown_allowed(self):
        for name in ("SPECIFICITY_CODEBOOK.md", "CODER_INSTRUCTIONS.md"):
            path = self.packet / "blinded" / name
            path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        self.assertEqual(p.verify_packet_integrity(self.packet)["files"]["CODER_INSTRUCTIONS.md"]["match"], "exact")

    def test_empty_adjudication_finalizes(self):
        self.run_silent(p.make_adjudication)
        self.run_silent(p.finalize_blind)
        final = p.load_json(self.packet / "blinded/BLIND_CODING_FINAL.json")
        self.assertEqual(final["adjudication"]["cards"], 0)
        self.assertIn("prereg/API_PILOT_0.1_B1A_CHANGE_RECORD.json", final["input_files_sha256"])

    def test_disagreement_and_unanimous_uncertainty(self):
        for coder in self.paths:
            path = self.paths[coder]; value = p.load_json(path)
            for row in value["codes"]:
                if row["card_id"] == self.ids[0]: row["code"] = "U"
                if row["card_id"] == self.ids[1]: row["code"] = "0" if coder == "C3" else "1"
                if row["card_id"] == self.ids[2]: row["code"] = {"C1":"1", "C2":"0", "C3":"U"}[coder]
            p.write_json(path, value)
        self.run_silent(p.make_adjudication)
        adj = p.load_json(self.packet / "blinded/ADJUDICATION_PACKET.json")
        self.assertEqual([c["card_id"] for c in adj["cards"]], self.ids[1:3])
        self.assertTrue(all(set(c) == {"card_id", "passage", "question"} for c in adj["cards"]))
        self.args.adjudication = self.root / "ADJ.json"
        p.write_json(self.args.adjudication, {"schema_version":"au-specificity-codes-v1", "packet_id":p.ORIGINAL_PACKET_ID,
            "coder_id":"FOUNDER_ADJUDICATOR", "codes":[{"card_id":self.ids[1],"code":"0"},{"card_id":self.ids[2],"code":"U"}]})
        self.run_silent(p.finalize_blind)
        final = p.load_json(self.packet / "blinded/BLIND_CODING_FINAL.json")
        self.assertEqual([c["final_code"] for c in final["cards"][:3]], ["U", "0", "U"])
        adj["cards"][0]["passage"] += " altered"
        p.write_json(self.packet / "blinded/ADJUDICATION_PACKET.json", adj)
        with self.assertRaisesRegex(ValueError, "card text"):
            self.run_silent(p.finalize_blind)

    def test_bad_code_files_rejected(self):
        path = self.paths["C1"]; original = p.load_json(path)
        for kind in ("omitted", "duplicate", "reordered", "numeric", "wrong_coder", "wrong_packet"):
            value = json.loads(json.dumps(original))
            if kind == "omitted": value["codes"].pop()
            if kind == "duplicate": value["codes"].append(value["codes"][0])
            if kind == "reordered": value["codes"].reverse()
            if kind == "numeric": value["codes"][0]["code"] = 1
            if kind == "wrong_coder": value["coder_id"] = "C2"
            if kind == "wrong_packet": value["packet_id"] = "wrong"
            p.write_json(path, value)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                p.validate_codes(path, self.packet / "blinded/CODER_C1.json", "C1")


if __name__ == "__main__":
    unittest.main()

"""Manzuri store tests — the version-lock rule is the product.
Run: python3 -m unittest discover -s tests"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from store import Store  # noqa: E402


class ManzuriStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.store = Store(self.tmp.name)
        self.client = self.store.create_client("Sharma Sweets")

    def tearDown(self):
        self.store.close()

    def test_client_token_is_long_and_unique(self):
        other = self.store.create_client("Other")
        self.assertGreaterEqual(len(self.client["token"]), 24)
        self.assertNotEqual(self.client["token"], other["token"])
        self.assertEqual(self.store.client_by_token(self.client["token"])["name"], "Sharma Sweets")
        self.assertIsNone(self.store.client_by_token("nope"))

    def test_approval_records_the_version_seen(self):
        post = self.store.add_post(self.client["id"], "Mon 1 Dec", "Diwali mithai!", None)
        decided = self.store.decide(post["id"], "approved")
        self.assertEqual(decided["status"], "approved")
        hist = self.store.history(post["id"])
        self.assertEqual(hist[-1]["version_seen"], 1)

    def test_edit_after_approval_voids_it(self):
        post = self.store.add_post(self.client["id"], "Mon 1 Dec", "Caption A", None)
        self.store.decide(post["id"], "approved")
        edited = self.store.edit_post(post["id"], caption="Caption B")
        self.assertTrue(edited["voided"])
        self.assertEqual(edited["status"], "pending")
        self.assertEqual(edited["version"], 2)
        actions = [h["action"] for h in self.store.history(post["id"])]
        self.assertEqual(actions, ["approved", "voided"])

    def test_noop_edit_does_not_void(self):
        post = self.store.add_post(self.client["id"], "Mon 1 Dec", "Same", None)
        self.store.decide(post["id"], "approved")
        edited = self.store.edit_post(post["id"], caption="Same")
        self.assertFalse(edited["voided"])
        self.assertEqual(edited["status"], "approved")
        self.assertEqual(edited["version"], 1)

    def test_change_request_requires_a_kind(self):
        post = self.store.add_post(self.client["id"], "Tue 2 Dec", "Caption", None)
        with self.assertRaises(ValueError):
            self.store.decide(post["id"], "changes")
        decided = self.store.decide(post["id"], "changes", note_kind="caption",
                                    note_text="Price galat hai")
        self.assertEqual(decided["status"], "changes")
        self.assertEqual(self.store.history(post["id"])[-1]["note_kind"], "caption")

    def test_export_lists_only_currently_approved(self):
        p1 = self.store.add_post(self.client["id"], "Mon 1 Dec", "One", None)
        p2 = self.store.add_post(self.client["id"], "Tue 2 Dec", "Two", None)
        p3 = self.store.add_post(self.client["id"], "Wed 3 Dec", "Three", None)
        self.store.decide(p1["id"], "approved")
        self.store.decide(p2["id"], "changes", note_kind="both")
        self.store.decide(p3["id"], "approved")
        self.store.edit_post(p3["id"], caption="Three — revised")  # voids p3
        exported = self.store.export_checklist(self.client["id"])
        self.assertEqual([p["id"] for p in exported], [p1["id"]])

    def test_client_counts(self):
        post = self.store.add_post(self.client["id"], "Mon 1 Dec", "One", None)
        self.store.decide(post["id"], "approved")
        row = [c for c in self.store.list_clients() if c["id"] == self.client["id"]][0]
        self.assertEqual((row["posts"], row["approved"], row["pending"]), (1, 1, 0))


if __name__ == "__main__":
    unittest.main()

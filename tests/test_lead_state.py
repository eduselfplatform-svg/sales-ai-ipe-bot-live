import os
import shutil
import tempfile
import unittest

# Test uchun temp katalogni sozlash
temp_dir = tempfile.mkdtemp()
os.environ["LEAD_STATE_PATH"] = os.path.join(temp_dir, "test_lead_state.json")
os.environ["CONVERSATION_HISTORY_LIMIT"] = "3"

import config
import lead_state

config.LEAD_STATE_PATH = os.path.join(temp_dir, "test_lead_state.json")
config.CONVERSATION_HISTORY_LIMIT = 3


class TestLeadState(unittest.TestCase):
    def setUp(self):
        lead_state._state_cache = {}
        if os.path.exists(config.LEAD_STATE_PATH):
            os.remove(config.LEAD_STATE_PATH)

    def tearDown(self):
        lead_state._state_cache = None

    def test_create_and_get_lead(self):
        lead, is_new = lead_state.get_or_create_lead(
            lead_id=12345,
            name="Dilnoza",
            username="dilnoza_01",
            role_context="sales",
        )
        self.assertTrue(is_new)
        self.assertEqual(lead["name"], "Dilnoza")
        self.assertEqual(lead["stage"], "new")

        # Qayta chaqirilganda mavjudini qaytarishi kerak
        lead2, is_new2 = lead_state.get_or_create_lead(lead_id=12345)
        self.assertFalse(is_new2)
        self.assertEqual(lead2["name"], "Dilnoza")

    def test_update_lead(self):
        lead_state.get_or_create_lead(lead_id=999)
        updated = lead_state.update_lead(
            999,
            stage="demo_invited",
            assigned_admin_name="Alisher",
            assigned_admin_id=777,
        )
        self.assertEqual(updated["stage"], "demo_invited")
        self.assertEqual(updated["assigned_admin_name"], "Alisher")

        # Fayldan qayta o'qish
        lead_state._state_cache = None
        reloaded = lead_state.get_lead(999)
        self.assertIsNotNone(reloaded)
        self.assertEqual(reloaded["stage"], "demo_invited")

    def test_history_limit(self):
        lead_id = 555
        lead_state.get_or_create_lead(lead_id)

        # 4 ta xabar qo'shamiz (limit=3)
        lead_state.append_history(lead_id, "user", "Xabar 1")
        lead_state.append_history(lead_id, "assistant", "Xabar 2")
        lead_state.append_history(lead_id, "user", "Xabar 3")
        lead_state.append_history(lead_id, "assistant", "Xabar 4")

        history = lead_state.get_conversation_history(lead_id)
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]["content"], "Xabar 2")
        self.assertEqual(history[2]["content"], "Xabar 4")


if __name__ == "__main__":
    unittest.main()

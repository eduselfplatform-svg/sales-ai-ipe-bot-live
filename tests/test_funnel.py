import unittest
import funnel


class TestFunnel(unittest.TestCase):
    def test_build_funnel_keyboard(self):
        keyboard = funnel.build_funnel_keyboard(lead_id=123)
        self.assertIsNotNone(keyboard)
        # 7 ta bosqich (4 qator) + 1 ta AI boshqaruv tugmasi (1 qator) = 5 ta qator
        self.assertEqual(len(keyboard.inline_keyboard), 5)

        first_button = keyboard.inline_keyboard[0][0]
        self.assertEqual(first_button.callback_data, "stage:123:new")
        self.assertIn("Yangi", first_button.text)

        toggle_button = keyboard.inline_keyboard[4][0]
        self.assertEqual(toggle_button.callback_data, "toggle_ai:123")
        self.assertIn("AI", toggle_button.text)

    def test_build_funnel_text(self):
        lead = {
            "name": "Rustam & Botir",
            "username": "rustam_coder",
            "stage": "course_recommended",
            "assigned_admin_name": "Sardor",
            "interest_note": "Frontend kursi <HTML/CSS>",
            "note": "Kechki vaqt qulay",
            "updated_at": "2026-09-29T16:00:00",
        }
        text = funnel.build_funnel_text(lead)
        # HTML xavfsiz bo'lishi kerak
        self.assertIn("&amp;", text)  # "Rustam & Botir" -> "Rustam &amp; Botir"
        self.assertIn("&lt;HTML/CSS&gt;", text)
        self.assertIn("@rustam_coder", text)
        self.assertIn("Sardor", text)
        self.assertIn("🎯 Kurs tavsiya qilindi", text)


if __name__ == "__main__":
    unittest.main()

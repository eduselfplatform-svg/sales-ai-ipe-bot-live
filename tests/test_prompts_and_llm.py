import unittest
from llm_client import parse_llm_response
from prompts import build_system_prompt, ROLE_RECEPTION, ROLE_SALES


class TestPromptsAndLLM(unittest.TestCase):
    def test_build_system_prompt_reception(self):
        prompt = build_system_prompt(ROLE_RECEPTION, "Ish vaqti: 09:00 - 18:00")
        self.assertIn("Qabulxona (Reception) Ma'muri", prompt)
        self.assertIn("Ish vaqti: 09:00 - 18:00", prompt)
        self.assertIn("qabulxona xodimisan", prompt)
        self.assertNotIn("MALAKALASH SAVOLLARI", prompt)

    def test_build_system_prompt_sales(self):
        prompt = build_system_prompt(ROLE_SALES, "Python kursi: 1,500,000 so'm")
        self.assertIn("Kurs Maslahatchisi", prompt)
        self.assertIn("Python kursi: 1,500,000 so'm", prompt)
        self.assertIn("BEPUL DEMO DARSGA", prompt)
        self.assertIn("MALAKALASH SAVOLLARI", prompt)

    def test_parse_llm_response_standard(self):
        raw = (
            "Assalomu alaykum! Bizda Python Backend kursi mavjud, haftada 3 kun bo'ladi.\n\n"
            "---LEAD_META---\n"
            "stage: in_conversation\n"
            'interest: "Python backend kursi"\n'
            'note: "Kechki guruh qidirmoqda"\n'
            "handoff_needed: false\n"
            "---END---"
        )
        user_text, meta = parse_llm_response(raw)
        self.assertEqual(user_text, "Assalomu alaykum! Bizda Python Backend kursi mavjud, haftada 3 kun bo'ladi.")
        self.assertEqual(meta.get("stage"), "in_conversation")
        self.assertEqual(meta.get("interest"), "Python backend kursi")
        self.assertEqual(meta.get("note"), "Kechki guruh qidirmoqda")
        self.assertFalse(meta.get("handoff_needed"))

    def test_parse_llm_response_handoff_and_stages(self):
        raw = (
            "Kechirasiz, maxsus chegirma bo'yicha ma'lumotni rahbarimizdan aniqlab beraman.\n"
            "---LEAD_META---\n"
            "stage: demo_invited\n"
            "handoff_needed: true\n"
            "---END---"
        )
        user_text, meta = parse_llm_response(raw)
        self.assertEqual(meta.get("stage"), "demo_invited")
        self.assertTrue(meta.get("handoff_needed"))

    def test_parse_llm_response_invalid_format_fallback(self):
        raw = "Oddiy xabar, LLM meta blokini yozishni unutib qoldirdi."
        user_text, meta = parse_llm_response(raw)
        self.assertEqual(user_text, raw)
        self.assertEqual(meta, {})

    def test_parse_llm_response_invalid_stage_filtered(self):
        raw = (
            "Salom!\n"
            "---LEAD_META---\n"
            "stage: random_unsupported_stage\n"
            "handoff_needed: false\n"
            "---END---"
        )
        user_text, meta = parse_llm_response(raw)
        self.assertIsNone(meta.get("stage"))


if __name__ == "__main__":
    unittest.main()

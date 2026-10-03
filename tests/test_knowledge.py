import os
import tempfile
import unittest

temp_dir = tempfile.mkdtemp()
os.environ["KNOWLEDGE_CACHE_PATH"] = os.path.join(temp_dir, "test_knowledge_cache.json")

import config
import knowledge


class TestKnowledge(unittest.TestCase):
    def setUp(self):
        knowledge._knowledge_cache = {"admin": {}, "sales": {}}
        knowledge._loaded = True

    def test_append_and_get_knowledge(self):
        knowledge.append_knowledge("admin", 101, "Maktab manzili: Chilonzor, 5-mavze.")
        knowledge.append_knowledge("sales", 202, "Python kursi narxi: 1,200,000 so'm.")

        reception_k = knowledge.get_knowledge("reception")
        self.assertIn("QABULXONA VA UMUMIY QOIDALAR", reception_k)
        self.assertIn("Chilonzor, 5-mavze", reception_k)
        self.assertIn("Python kursi narxi", reception_k)

        sales_k = knowledge.get_knowledge("sales")
        self.assertIn("KURSLAR, NARXLAR VA AKSIYALAR", sales_k)
        self.assertIn("Python kursi narxi", sales_k)
        self.assertIn("Chilonzor, 5-mavze", sales_k)

    def test_update_post(self):
        knowledge.append_knowledge("admin", 101, "Eski manzil")
        knowledge.append_knowledge("admin", 101, "Yangi manzil: Yunusobod")

        text = knowledge.get_raw_knowledge_text("admin")
        self.assertNotIn("Eski manzil", text)
        self.assertIn("Yangi manzil: Yunusobod", text)


if __name__ == "__main__":
    unittest.main()

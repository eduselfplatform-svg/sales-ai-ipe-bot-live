import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

temp_dir = tempfile.mkdtemp()
os.environ["LEAD_STATE_PATH"] = os.path.join(temp_dir, "sim_lead_state.json")
os.environ["KNOWLEDGE_CACHE_PATH"] = os.path.join(temp_dir, "sim_knowledge_cache.json")
os.environ["BOT_TOKEN"] = "123456:FAKE_TOKEN"
os.environ["BUSINESS_CONNECTION_RECEPTION_ID"] = "biz_reception_001"
os.environ["BUSINESS_CONNECTION_SALES_ID"] = "biz_sales_002"
os.environ["ADMIN_CHAT_ID"] = "-1004444"
os.environ["FUNNEL_CHANNEL_ID"] = "-1003333"
os.environ["ADMIN_IDS"] = "111111,222222"

import config
import funnel
import knowledge
import lead_state
from handlers.business import handle_business_message
from handlers.funnel_buttons import handle_stage_callback

# Config ob'ektidagi qiymatlarni to'g'ridan-to'g'ri o'rnatamiz
config.LEAD_STATE_PATH = os.path.join(temp_dir, "sim_lead_state.json")
config.KNOWLEDGE_CACHE_PATH = os.path.join(temp_dir, "sim_knowledge_cache.json")
config.BOT_TOKEN = "123456:FAKE_TOKEN"
config.BUSINESS_CONNECTION_RECEPTION_ID = "biz_reception_001"
config.BUSINESS_CONNECTION_SALES_ID = "biz_sales_002"
config.ADMIN_CHAT_ID = -1004444
config.FUNNEL_CHANNEL_ID = -1003333
config.ADMIN_IDS = {111111, 222222}


class TestEndToEndSimulation(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        lead_state._state_cache = {}
        knowledge._knowledge_cache = {
            "admin": {"1": "Ish vaqti: 09:00 dan 19:00 gacha. Manzil: Chilonzor."},
            "sales": {"2": "IT kurslari: Python, Web frontend, Kiberxavfsizlik. Narxi: 1,500,000 so'm/oy."},
        }
        knowledge._loaded = True

    @patch("handlers.business.ask_deepseek")
    async def test_reception_message_flow(self, mock_ask_deepseek):
        # 1. Mijoz reception profiliga yozadi
        mock_ask_deepseek.return_value = (
            "Assalomu alaykum! IPE School ish vaqti 09:00 dan 19:00 gacha.",
            {"stage": "new", "interest": "", "note": "", "handoff_needed": False}
        )

        mock_bot = AsyncMock()
        mock_context = MagicMock()
        mock_context.bot = mock_bot

        # Mock update
        mock_update = MagicMock()
        mock_update.edited_business_message = None
        mock_msg = MagicMock()
        mock_msg.business_connection_id = "biz_reception_001"
        mock_msg.chat.id = 888001
        mock_msg.from_user.id = 888001
        mock_msg.from_user.full_name = "Jasur Aliyev"
        mock_msg.from_user.username = "jasur_a"
        mock_msg.from_user.is_bot = False
        mock_msg.text = "Assalomu alaykum, ish vaqtingiz qanday?"
        mock_update.business_message = mock_msg

        await handle_business_message(mock_update, mock_context)

        # Tekshiruvlar:
        # a) Lead yaratilgan bo'lishi kerak
        lead = lead_state.get_lead(888001)
        self.assertIsNotNone(lead)
        self.assertEqual(lead["role_context"], "reception")
        self.assertEqual(lead["name"], "Jasur Aliyev")

        # b) ask_deepseek "reception" roli bilan chaqirilgan bo'lishi kerak
        mock_ask_deepseek.assert_called_once()
        call_role = mock_ask_deepseek.call_args.kwargs["role"]
        self.assertEqual(call_role, "reception")

        # c) Mijozga javob yuborilgan
        mock_bot.send_message.assert_any_call(
            chat_id=888001,
            text="Assalomu alaykum! IPE School ish vaqti 09:00 dan 19:00 gacha.",
            business_connection_id="biz_reception_001",
        )

    @patch("handlers.business.ask_deepseek")
    async def test_sales_message_and_stage_update(self, mock_ask_deepseek):
        # 2. Mijoz sales profiliga yozadi
        mock_ask_deepseek.return_value = (
            "Assalomu alaykum! Bizda IT yo'nalishida Python va Frontend kurslari bor. Kim uchun qidiryapsiz?",
            {
                "stage": "in_conversation",
                "interest": "IT kurslari",
                "note": "Yangi o'rganuvchi",
                "handoff_needed": False,
            }
        )

        mock_bot = AsyncMock()
        # send_message yangi post id sini 5001 deb qaytarsin
        sent_msg_mock = MagicMock()
        sent_msg_mock.message_id = 5001
        mock_bot.send_message.return_value = sent_msg_mock

        mock_context = MagicMock()
        mock_context.bot = mock_bot

        mock_update = MagicMock()
        mock_update.edited_business_message = None
        mock_msg = MagicMock()
        mock_msg.business_connection_id = "biz_sales_002"
        mock_msg.chat.id = 999002
        mock_msg.from_user.id = 999002
        mock_msg.from_user.full_name = "Dilnoza"
        mock_msg.from_user.username = "dilnoza"
        mock_msg.from_user.is_bot = False
        mock_msg.text = "Salom, IT kurslaringiz bormi?"
        mock_update.business_message = mock_msg

        await handle_business_message(mock_update, mock_context)

        lead = lead_state.get_lead(999002)
        self.assertEqual(lead["role_context"], "sales")
        self.assertEqual(lead["stage"], "in_conversation")
        self.assertEqual(lead["interest_note"], "IT kurslari")

    async def test_funnel_button_authorization(self):
        # Lead yaratamiz
        lead_state.get_or_create_lead(777, name="Bobur")

        mock_context = MagicMock()

        # Ruxsatsiz foydalanuvchi tugma bossa
        mock_query_unauth = AsyncMock()
        mock_query_unauth.data = "stage:777:demo_invited"
        mock_query_unauth.from_user.id = 99999999  # ADMIN_IDS da yo'q
        mock_update_unauth = MagicMock()
        mock_update_unauth.callback_query = mock_query_unauth

        await handle_stage_callback(mock_update_unauth, mock_context)
        mock_query_unauth.answer.assert_called_with("Sizda ushbu amalni bajarish uchun ruxsat yo'q!", show_alert=True)
        # Bosqich o'zgarmasligi kerak
        lead = lead_state.get_lead(777)
        self.assertEqual(lead["stage"], "new")

        # Ruxsatli admin tugma bossa (111111)
        mock_query_auth = AsyncMock()
        mock_query_auth.data = "stage:777:demo_invited"
        mock_query_auth.from_user.id = 111111
        mock_query_auth.from_user.full_name = "Alisher Admin"
        mock_update_auth = MagicMock()
        mock_update_auth.callback_query = mock_query_auth

        await handle_stage_callback(mock_update_auth, mock_context)
        lead = lead_state.get_lead(777)
        self.assertEqual(lead["stage"], "demo_invited")
        self.assertEqual(lead["assigned_admin_id"], 111111)
        self.assertEqual(lead["assigned_admin_name"], "Alisher Admin")
        mock_query_auth.edit_message_text.assert_called_once()

    @patch("handlers.business.ask_deepseek")
    async def test_direct_message_flow(self, mock_ask_deepseek):
        from handlers.business import handle_direct_message

        mock_ask_deepseek.return_value = (
            "Assalomu alaykum! IPE School kurslariga xush kelibsiz.",
            {"stage": "in_conversation", "interest": "Backend", "note": "", "handoff_needed": False}
        )

        mock_bot = AsyncMock()
        mock_context = MagicMock()
        mock_context.bot = mock_bot

        # Mock direct message update (@ipesalesai_bot ga to'g'ridan-to'g'ri yozilgan)
        mock_update = MagicMock()
        mock_msg = AsyncMock()
        mock_msg.text = "Salom, kurslaringiz haqida ma'lumot bering"
        mock_user = MagicMock()
        mock_user.id = 555001
        mock_user.full_name = "Nodir"
        mock_user.username = "nodir_dev"
        mock_user.is_bot = False
        mock_chat = MagicMock()
        mock_chat.id = 555001

        mock_update.effective_message = mock_msg
        mock_update.effective_user = mock_user
        mock_update.effective_chat = mock_chat

        await handle_direct_message(mock_update, mock_context)

        # Tekshiramiz:
        # a) Lead yaratildi
        lead = lead_state.get_lead(555001)
        self.assertIsNotNone(lead)
        self.assertEqual(lead["name"], "Nodir")

        # b) ask_deepseek chaqirildi
        mock_ask_deepseek.assert_called_once()

        # c) reply_text orqali javob berildi
        mock_msg.reply_text.assert_called_once_with(
            "Assalomu alaykum! IPE School kurslariga xush kelibsiz."
        )


if __name__ == "__main__":
    unittest.main()

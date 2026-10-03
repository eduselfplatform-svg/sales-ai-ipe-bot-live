import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

temp_dir = tempfile.mkdtemp()
os.environ["LEAD_STATE_PATH"] = os.path.join(temp_dir, "takeover_lead_state.json")
os.environ["BOT_TOKEN"] = "123456:FAKE_TOKEN"

import config
import lead_state
from handlers.business import handle_business_message
from handlers.funnel_buttons import handle_toggle_ai_callback

config.LEAD_STATE_PATH = os.path.join(temp_dir, "takeover_lead_state.json")
config.ADMIN_CHAT_ID = -1004444
config.FUNNEL_CHANNEL_ID = -1003333
config.ADMIN_IDS = {6047410688}


class TestHumanTakeover(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        lead_state._state_cache = {}

    def test_lead_state_ai_toggle(self):
        lead_id = "111222"
        lead_state.get_or_create_lead(lead_id, name="Test Lead")

        # Boshida AI faol
        is_active, _ = lead_state.is_ai_active_for_lead(lead_id)
        self.assertTrue(is_active)

        # Xodim shaxsan javob yozganda (takeover)
        lead_state.record_human_reply(lead_id, "Salom, men o'zim sizga yordam beraman.")
        is_active, reason = lead_state.is_ai_active_for_lead(lead_id)
        self.assertFalse(is_active)
        self.assertIn("Xodim shaxsan muloqot qilmoqda", reason)

        # AI qayta yoqilganda
        lead_state.set_ai_enabled(lead_id, True)
        is_active, _ = lead_state.is_ai_active_for_lead(lead_id)
        self.assertTrue(is_active)

    @patch("handlers.business.ask_deepseek")
    async def test_customer_message_when_ai_disabled(self, mock_ask_deepseek):
        lead_id = 333444
        lead_state.get_or_create_lead(lead_id, name="Ali")
        lead_state.set_ai_enabled(lead_id, False)

        mock_bot = AsyncMock()
        mock_context = MagicMock()
        mock_context.bot = mock_bot

        mock_update = MagicMock()
        mock_update.edited_business_message = None
        mock_msg = MagicMock()
        mock_msg.business_connection_id = "biz_conn_dynamic"
        mock_msg.chat.id = lead_id
        mock_msg.from_user.id = lead_id  # Mijoz yozdi
        mock_msg.from_user.full_name = "Ali"
        mock_msg.from_user.username = "ali"
        mock_msg.from_user.is_bot = False
        mock_msg.text = "Kurs narxi qancha?"
        mock_update.business_message = mock_msg

        await handle_business_message(mock_update, mock_context)

        # DeepSeek chaqirilmasligi kerak!
        mock_ask_deepseek.assert_not_called()

        # Mijozga avtomatik javob yuborilmagan bo'lishi kerak!
        self.assertFalse(any(
            call.kwargs.get("chat_id") == lead_id and "business_connection_id" in call.kwargs
            for call in mock_bot.send_message.call_args_list
        ))

        # Admin chatga ogohlantirish borgan bo'lishi kerak
        admin_calls = [
            call for call in mock_bot.send_message.call_args_list
            if call.kwargs.get("chat_id") == config.ADMIN_CHAT_ID
        ]
        self.assertTrue(len(admin_calls) > 0)
        self.assertIn("Xodim nazoratida", admin_calls[0].kwargs.get("text", ""))

    async def test_owner_bot_off_command(self):
        lead_id = 555666
        lead_state.get_or_create_lead(lead_id, name="Vali")

        mock_bot = AsyncMock()
        mock_context = MagicMock()
        mock_context.bot = mock_bot

        # Xodim mijoz chatida #bot off deb yozdi
        mock_update = MagicMock()
        mock_update.edited_business_message = None
        mock_msg = MagicMock()
        mock_msg.business_connection_id = "biz_conn_dynamic"
        mock_msg.chat.id = lead_id
        mock_msg.from_user.id = 999999  # Xodim (sender.id != chat.id)
        mock_msg.from_user.is_bot = False
        mock_msg.text = "#bot off"
        mock_update.business_message = mock_msg

        await handle_business_message(mock_update, mock_context)

        is_active, _ = lead_state.is_ai_active_for_lead(lead_id)
        self.assertFalse(is_active)


if __name__ == "__main__":
    unittest.main()

# IPE School — Reception + Sotuv (Sales) AI Boti (Telegram Business API)

Ushbu loyiha **IPE School** o'quv markazining rasmiy Telegram Business akkauntlariga kelgan mijozlar (leadlar) bilan avtomatlashtirilgan muloqot o'rnatish, ehtiyojlarini aniqlash (discovery), mos kurslarni tavsiya qilish va bepul demo darsga taklif qilish uchun yaratilgan backend tizimidir.

---

## 🚀 Asosiy Imkoniyatlar va Arxitektura

1. **Telegram Business Chat Automation (Dinamik Ulanish):**
   - Telegram Premium hisobidan *Sozlamalar ➡️ Telegram Business ➡️ Chatbots* orqali botni shaxsiy akkauntga ulash kifoya.
   - Alohida connection ID'larni `.env` da yozish **shart emas** — bot Telegram API orqali kelgan ulanishni avtomatik ravishda taniydi.
   - AI bitta qolipda ham **Qabulxona (Reception)**, ham **Sotuv Konsultanti (Sales)** sifatida ishlaydi.

2. **Xodim Uchun Erkin Muloqot (Human Takeover & AI Control):**
   - **Xodim yozganda AI xalaqit bermaydi:** Xodim mijoz chatiga shaxsan o'zi xabar yozishi bilanoq, AI avtomatik ravishda kutish rejimiga o'tadi va muloqotga aralashmaydi.
   - **Chat ichidagi buyruqlar:** Xodim mijoz chatida `#bot off` (yoki `/bot off`) deb yozsa, AI to'xtaydi. `#bot on` (yoki `/bot on`) deb yozsa, AI avto-javoblari qayta yoqiladi.
   - **Interaktiv tugma:** Varonka postida va Admin chatiga kelgan bildirishnomalarda `[⏸ AI ni to'xtatish]` va `[▶️ AI ni yoqish]` tugmalari mavjud.

3. **Dinamik Bilim Bazasi va Demo Ma'lumotlar:**
   - Ikkita Telegram kanali orqali boshqariladi:
     - `ADMIN_KNOWLEDGE_CHANNEL_ID` — manzil, ish vaqti, filiallar, qabul qoidalari.
     - `SALES_KNOWLEDGE_CHANNEL_ID` — IT va til kurslari, narxlar, aksiyalar, bepul demo dars.
   - Kanallarni tezda to'ldirish uchun `python populate_channels.py` skripti mavjud.

4. **Savdo Varonkasi (Kanban) Kanali:**
   - Har bir yangi lead uchun `FUNNEL_CHANNEL_ID` kanalida interaktiv HTML post yaratiladi.
   - Bosqichlar: `🆕 Yangi`, `💬 Muloqotda`, `🎯 Kurs tavsiya qilindi`, `📅 Demo taklif qilindi`, `✅ Demo tasdiqlandi`, `🏆 Sotib oldi`, `❌ Qiziqmadi`.
   - Bosqich o'zgarganda mavjud post tahrirlanadi (`edit_message_text`).
   - Adminlar inline tugmalar orqali bosqichni o'zgartirishi va o'zlarini mas'ul qilib biriktirishi mumkin.

5. **DeepSeek LLM + Structured Output:**
   - OpenAI SDK orqali DeepSeek API (`deepseek-chat`) bilan asinxron ishlash (`asyncio.to_thread`).
   - "Ultra-effektiv" tizim prompti va yashirin `---LEAD_META---` bloklari orqali `stage`, `interest`, `note`, `handoff_needed` parametrlari avtomatik ajratib olinadi.

6. **Xodimlar uchun Live Bildirishnomalar va Shaxsiy DM:**
   - Har bir mijoz yozganda `ADMIN_CHAT_ID` guruhiga xabar keladi.
   - Agar mijozga muayyan admin biriktirilgan bo'lsa, uning shaxsiy chatiga (DM) xabar boradi.

---

## 📂 Fayl Tuzilishi

```
sales_bot/
├── main.py                   # Asosiy dastur, webhook/polling va handlerlar ro'yxati
├── config.py                 # .env parametrlarini yuklash va validatsiya
├── llm_client.py             # DeepSeek LLM chaqiruvi, retry va LEAD_META parse
├── prompts.py                # "Ultra-effektiv" tizim prompti (Combined, Reception & Sales)
├── knowledge.py              # Bilim keshini boshqarish va tayyor demo ma'lumotlar
├── lead_state.py             # lead_state.json lokal indeksi va Human Takeover nazorati
├── funnel.py                 # Varonka kartochkasi (HTML) va AI toggle tugmalari
├── populate_channels.py      # Bilim kanallariga demo postlarni avtomatik joylash skripti
├── handlers/
│   ├── business.py           # business_message, xodim nazorati va connection handlerlari
│   ├── knowledge_channels.py # Bilim kanallari postlarini tinglash
│   ├── funnel_buttons.py     # Varonka bosqichlari va AI toggle callback handleri
│   └── admin_register.py     # Admin /start, /status va /test_dm buyruqlari
├── tests/
│   ├── test_lead_state.py    # Lead holati testlari
│   ├── test_prompts_and_llm.py # Prompt va LLM parse testlari
│   ├── test_funnel.py        # Varonka kartochkasi va tugmalar testlari
│   ├── test_knowledge.py     # Bilim keshi testlari
│   ├── test_human_takeover.py # Xodim erkin muloqoti va AI to'xtatish testlari
│   └── test_simulation.py   # E2E biznes jarayonlar simulyatsiyasi
├── requirements.txt          # Python kutubxonalari
├── .env.example              # Konfiguratsiya namunasi
├── render.yaml               # Render.com deployment manifesti
├── Procfile                  # Dasturni ishga tushirish buyrug'i
└── README.md                 # Loyiha qo'llanmasi
```

---

## ⚙️ O'rnatish va Sozlash

### 1. Talablar
- Python 3.11 yoki undan yuqori
- Telegram Bot Token ([@BotFather](https://t.me/BotFather) orqali)
- DeepSeek API kaliti ([platform.deepseek.com](https://platform.deepseek.com))
- Telegram Premium obunasi (shaxsiy profilni chatbotga ulash uchun)

### 2. O'rnatish
```bash
git clone <repo-url>
cd "sales ipe bot"

# Virtual muhit yaratish
python -m venv venv
source venv/bin/activate  # Windows uchun: venv\Scripts\activate

# Kutubxonalarni o'rnatish
pip install -r requirements.txt
```

### 3. `.env` Faylini Sozlash
```env
BOT_TOKEN=8723693022:AAF0Hu4QJxpWkebdozPaeGZRA6fVqPnZd68

ADMIN_KNOWLEDGE_CHANNEL_ID=-1004363930246
SALES_KNOWLEDGE_CHANNEL_ID=-1004431735278
FUNNEL_CHANNEL_ID=-1004405238989
ADMIN_CHAT_ID=6047410688
ADMIN_IDS=6047410688

DEEPSEEK_API_KEY=sk-66fd11fa15594054b47e2185674f47be
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com

RUN_MODE=polling  # Mahalliy test uchun 'polling', serverda 'webhook'
PORT=8080
```

---

## 📢 Kanallarni Demo Ma'lumotlar Bilan To'ldirish

Admin va Sales bilim kanallariga IPE School haqidagi to'liq ma'lumotlarni bir zumda joylash uchun quyidagi skriptni ishlating:

```bash
python populate_channels.py
```

Ushbu skript:
1. `data/knowledge_cache.json` faylini tayyor demo ma'lumotlar bilan to'ldiradi.
2. Bot orqali `ADMIN_KNOWLEDGE_CHANNEL_ID` va `SALES_KNOWLEDGE_CHANNEL_ID` ga chiroyli formatdagi rasmiy postlarni joylaydi.

---

## 📱 Telegram Business Chatbotni Ulash (Chat Automation)

1. Telegram ilovasida Premium obunaga ega akkauntingizga kiring.
2. `Sozlamalar (Settings)` ➡️ `Telegram Business` ➡️ `Chatbots (Chat-botlar)` bo'limiga kiring.
3. Bot username'ini (`@ipesalesai_bot`) kiriting va ulanishga ruxsat bering.
4. Bo'ldi! Hech qanday connection ID larni qo'lda kiritish shart emas.

---

## 💬 Xodimning Mijoz Bilan Erkin Muloqot Qilishi

- **Avtomatik aniqlash:** Xodim mijozga shaxsan biror narsa yozsa, bot xodim javob berayotganini tushunadi va o'zining avto-javoblarini to'xtatadi.
- **Tezkor buyruqlar:** Mijoz bilan chat ichida `#bot off` deb yozsangiz AI to'xtaydi, `#bot on` deb yozsangiz yana qayta faollashadi.
- **Tugma orqali boshqaruv:** Admin chatiga kelgan har bir xabar ostidagi `[⏸ AI ni to'xtatish]` yoki `[▶️ AI ni yoqish]` tugmasini bosish orqali boshqarishingiz mumkin.

---

## 🧪 Sinovlarni Ishga Tushirish (Tests)

Barcha unit va integratsion testlarni ishga tushirish:
```bash
python -m pytest -v
```

19 ta test muvaffaqiyatli o'tadi:
- Human takeover va xodim erkin muloqot testlari
- Lead holatini boshqarish va tarixni qirqish
- Bilim kanallaridan kesh to'plash va demo ma'lumotlar
- Tizim promptlari va DeepSeek structured metadata parsi
- Savdo varonkasi vizual HTML matnlari va inline tugmalari
- To'liq simulyatsiya: Reception/Sales xabarlari, bosqich o'zgartirish

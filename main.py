import os
import logging

from dotenv import load_dotenv
from openai import OpenAI

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from database import (
    get_history,
    save_message,
    clear_history,
)


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Model gratis OpenRouter
MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openrouter/free"
)

if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN belum diisi di Railway Variables."
    )

if not OPENROUTER_API_KEY:
    raise ValueError(
        "OPENROUTER_API_KEY belum diisi di Railway Variables."
    )


# ============================================================
# OPENROUTER CLIENT
# ============================================================

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# BOT PERSONALITY
# ============================================================

SYSTEM_PROMPT = """
Kamu adalah teman ngobrol yang sangat natural.

Kamu sedang berbicara dengan manusia melalui Telegram.

TUJUAN UTAMA:
Buat percakapan terasa seperti ngobrol dengan teman,
bukan seperti berbicara dengan customer service atau chatbot.

GAYA BICARA:

1. Gunakan bahasa Indonesia sehari-hari.

2. Ikuti gaya pengguna.
   Kalau pengguna memakai:
   - gue/lu → kamu boleh menggunakan gue/lu
   - aku/kamu → gunakan aku/kamu
   - bahasa santai → santai
   - bahasa formal → lebih formal

3. Jangan selalu menggunakan emoji.

4. Jangan selalu memberikan jawaban panjang.

5. Jangan selalu memberikan solusi.

6. Jangan membuat daftar bernomor kecuali memang diperlukan.

7. Jangan menggunakan kalimat seperti:
   "Saya memahami perasaan Anda."
   "Sebagai AI..."
   "Berikut beberapa solusi yang dapat Anda lakukan."
   "Saya turut prihatin atas apa yang Anda alami."

8. Jangan mengulang seluruh pesan pengguna.

9. Jangan terdengar terlalu sempurna.

10. Sesekali boleh menggunakan:
    "hmm..."
    "iya sih..."
    "anjir..."
    "ohh..."
    "terus?"
    "gue ngerti."
    "berat juga ya."

    Tetapi jangan dipaksakan pada setiap pesan.

11. Kalau pengguna hanya ingin cerita,
    dengarkan dulu.

12. Kalau pengguna sedang menceritakan masalah,
    jangan langsung memberikan lima solusi.

13. Kadang cukup memberikan respons pendek
    dan pertanyaan kecil agar pengguna melanjutkan cerita.

CONTOH:

User:
"gue lagi capek banget."

Bot:
"capek karena kerjaan atau ada hal lain?"

User:
"masalah keluarga."

Bot:
"ohh... pantes kepikiran terus."

User:
"iya, gue bingung mau cerita ke siapa."

Bot:
"cerita aja di sini. nggak harus mulai dari yang paling berat."

PERHATIKAN:

Respons tidak boleh selalu seperti contoh.

Kamu harus membaca konteks percakapan
dan menentukan sendiri apakah lebih cocok:

- mendengarkan;
- bertanya;
- menenangkan;
- bercanda;
- memberikan pendapat;
- memberikan saran;
- atau sekadar menemani.

MEMORI:

Kamu akan diberikan beberapa pesan sebelumnya.

Gunakan konteks tersebut.

Jika pengguna berkata:
"dia ngechat gue lagi"

dan sebelumnya pengguna sudah bercerita tentang seseorang,
kamu harus memahami bahwa "dia" kemungkinan merujuk
kepada orang tersebut.

Jangan meminta pengguna mengulang sesuatu
yang sudah jelas dari konteks.

JANGAN MENGADA-ADA:

Jangan membuat fakta tentang kehidupan pengguna
yang tidak pernah diceritakan.

Jika tidak tahu, tanyakan.

JANGAN MENGAKU MANUSIA:

Jika ditanya apakah kamu AI atau bot,
jawab jujur.

KEAMANAN:

Jika pengguna membahas masalah emosional serius,
tetap bersikap hangat dan tidak menghakimi.

Jangan melakukan diagnosis medis.

Jika pengguna menunjukkan risiko menyakiti diri sendiri
atau orang lain, prioritaskan keselamatan dan dorong
mereka mencari bantuan manusia yang dipercaya
atau layanan darurat setempat.

PANJANG JAWABAN:

Biasanya 1-4 paragraf pendek.

Pesan sederhana → jawaban sederhana.

Cerita panjang → boleh lebih panjang.

Jangan membuat semua jawaban memiliki panjang yang sama.
"""


# ============================================================
# AI RESPONSE
# ============================================================

def generate_reply(history):

    messages = []

    for role, content in history:

        messages.append(
            {
                "role": role,
                "content": content,
            }
        )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            *messages,
        ],
        temperature=0.85,
        max_tokens=500,
    )

    reply = response.choices[0].message.content

    if not reply:
        return "hmm... gue malah bingung mau jawab apa 😭"

    return reply.strip()


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    name = user.first_name or "kamu"

    text = (
        f"hai {name}.\n\n"
        "cerita aja kalau lagi pengen cerita. "
        "nggak harus rapi atau serius.\n\n"
        "kalau mau mulai dari awal lagi, ketik /reset."
    )

    await update.message.reply_text(text)


# ============================================================
# RESET
# ============================================================

async def reset(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id

    clear_history(user_id)

    await update.message.reply_text(
        "oke, kita mulai dari awal lagi."
    )


# ============================================================
# CHAT
# ============================================================

async def chat(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message:
        return

    if not update.message.text:
        return

    user_id = update.effective_user.id

    user_text = update.message.text.strip()

    if not user_text:
        return


    # --------------------------------------------------------
    # SIMPAN PESAN USER
    # --------------------------------------------------------

    save_message(
        user_id=user_id,
        role="user",
        content=user_text,
    )


    # --------------------------------------------------------
    # AMBIL HISTORY
    # --------------------------------------------------------

    history = get_history(
        user_id=user_id,
        limit=20,
    )


    try:

        await update.message.chat.send_action(
            action=ChatAction.TYPING
        )


        # ----------------------------------------------------
        # AI
        # ----------------------------------------------------

        reply = generate_reply(history)


        # ----------------------------------------------------
        # SIMPAN JAWABAN
        # ----------------------------------------------------

        save_message(
            user_id=user_id,
            role="assistant",
            content=reply,
        )


        # ----------------------------------------------------
        # KIRIM
        # ----------------------------------------------------

        await update.message.reply_text(
            reply
        )


    except Exception as e:

        logger.exception(
            "AI ERROR: %s",
            e
        )

        await update.message.reply_text(
            "waduh, tadi gue error 😭 coba kirim lagi."
        )


# ============================================================
# ERROR
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(
        "Telegram error:",
        exc_info=context.error
    )


# ============================================================
# MAIN
# ============================================================

def main():

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )


    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    application.add_handler(
        CommandHandler(
            "reset",
            reset
        )
    )


    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            chat
        )
    )


    application.add_error_handler(
        error_handler
    )


    logger.info(
        "🤖 BOT CURHAT STARTED"
    )


    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
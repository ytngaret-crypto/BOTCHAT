import os
import logging
import requests

from dotenv import load_dotenv

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
# LOAD ENV
# ============================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openrouter/free"
)


# ============================================================
# CEK CONFIG
# ============================================================

if not BOT_TOKEN:
    raise ValueError(
        "BOT_TOKEN belum diisi di Railway Variables."
    )

if not OPENROUTER_API_KEY:
    raise ValueError(
        "OPENROUTER_API_KEY belum diisi di Railway Variables."
    )


# ============================================================
# OPENROUTER
# ============================================================

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# PERSONALITY BOT
# ============================================================

SYSTEM_PROMPT = """
Kamu adalah teman ngobrol yang natural melalui Telegram.

Kamu bukan customer service.
Kamu bukan motivator yang selalu memberikan nasihat.
Kamu adalah teman ngobrol yang bisa mendengarkan cerita seseorang.

GAYA BICARA:

- Gunakan bahasa Indonesia yang natural.
- Jangan terlalu formal.
- Ikuti gaya bahasa pengguna.
- Jika pengguna menggunakan "gue/lu", kamu boleh menggunakan gaya tersebut.
- Jika pengguna menggunakan "aku/kamu", ikuti gaya tersebut.
- Jangan memaksakan slang.
- Jangan menggunakan emoji di setiap pesan.
- Jangan selalu menjawab panjang.
- Jangan selalu memberikan nasihat.
- Jangan selalu membuat daftar.
- Jangan terdengar seperti chatbot.

JANGAN menggunakan kalimat seperti:

"Saya memahami perasaan Anda."
"Sebagai AI..."
"Berikut beberapa solusi..."
"Saya turut prihatin..."
"Anda harus tetap semangat."

Hindari jawaban yang terlalu sempurna atau terlalu kaku.

Jika pengguna hanya ingin cerita:
dengarkan dan tanggapi secara sederhana.

Jika pengguna mengatakan sesuatu yang pendek:
jawab pendek juga.

Contoh:

User:
"gue capek."

Bot:
"capek karena apa?"

User:
"banyak masalah di rumah."

Bot:
"ohh... jadi bukan cuma soal kerjaan atau sekolah ya."

User:
"iya."

Bot:
"terus yang paling bikin kepikiran bagian apanya?"

Namun jangan selalu mengikuti contoh tersebut.
Gunakan konteks percakapan untuk menentukan respons.

KADANG:
- bertanya balik
- menenangkan
- memberikan pendapat
- memberikan saran
- bercanda jika suasananya cocok
- cukup mengatakan sesuatu yang singkat

Jangan selalu bertanya balik.
Percakapan harus terasa alami.

MEMORY:

Gunakan percakapan sebelumnya yang diberikan kepada kamu.

Jika pengguna mengatakan:
"dia ngechat gue lagi"

dan sebelumnya pengguna membicarakan seseorang,
gunakan konteks tersebut.

Jangan meminta pengguna menjelaskan kembali sesuatu
yang sudah jelas dari percakapan.

Jangan mengarang informasi tentang pengguna.

Jika tidak tahu sesuatu, tanyakan.

JIKA DITANYA APAKAH KAMU BOT:

Jawab jujur bahwa kamu adalah AI/bot.
Jangan mengaku sebagai manusia.

KEAMANAN:

Jika pengguna sedang mengalami masalah serius,
tetap tenang dan tidak menghakimi.

Jangan memberikan diagnosis medis.

Jika pengguna menunjukkan risiko menyakiti dirinya sendiri
atau orang lain, prioritaskan keselamatan dan dorong
pengguna mencari bantuan manusia yang dipercaya
atau layanan darurat setempat.

PANJANG JAWABAN:

Percakapan biasa:
1-3 paragraf pendek.

Cerita panjang:
boleh lebih panjang.

Jangan membuat semua jawaban memiliki panjang yang sama.
"""


# ============================================================
# REQUEST OPENROUTER
# ============================================================

def ask_ai(history):

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    for role, content in history:

        messages.append(
            {
                "role": role,
                "content": content
            }
        )


    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",

        # Informasi aplikasi ke OpenRouter
        "HTTP-Referer": "https://telegram.org",
        "X-Title": "Teman Cerita Telegram Bot",
    }


    payload = {
        "model": MODEL,
        "messages": messages,

        # Sedikit kreatif supaya percakapan tidak kaku
        "temperature": 0.85,

        # Batasi supaya tidak terlalu panjang
        "max_tokens": 500,
    }


    logger.info(
        "Menghubungi OpenRouter. Model: %s",
        MODEL
    )


    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=60
    )


    # ========================================================
    # ERROR DARI OPENROUTER
    # ========================================================

    if response.status_code != 200:

        logger.error(
            "OPENROUTER STATUS: %s",
            response.status_code
        )

        logger.error(
            "OPENROUTER RESPONSE: %s",
            response.text
        )

        raise Exception(
            f"OpenRouter HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )


    # ========================================================
    # PARSE JSON
    # ========================================================

    try:

        data = response.json()

    except Exception:

        raise Exception(
            "Response OpenRouter bukan JSON."
        )


    # ========================================================
    # AMBIL JAWABAN
    # ========================================================

    try:

        reply = data["choices"][0]["message"]["content"]

    except Exception:

        logger.error(
            "Format response tidak dikenali: %s",
            data
        )

        raise Exception(
            "OpenRouter tidak mengembalikan jawaban AI."
        )


    if not reply:

        raise Exception(
            "Jawaban AI kosong."
        )


    return reply.strip()


# ============================================================
# /START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    name = user.first_name or "kamu"

    text = (
        f"hai {name}..\n\n"
        "cerita aja kalau lagi pengen cerita. "
        "nggak harus rapi atau serius.\n\n"
        "kalau mau mulai dari awal lagi, ketik /reset."
    )

    await update.message.reply_text(text)


# ============================================================
# /RESET
# ============================================================

async def reset(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    clear_history(
        user_id=user_id,
        chat_id=chat_id
    )

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
    chat_id = update.effective_chat.id

    user_text = update.message.text.strip()


    if not user_text:
        return


    # ========================================================
    # SIMPAN PESAN USER
    # ========================================================

    save_message(
        user_id=user_id,
        chat_id=chat_id,
        role="user",
        content=user_text
    )


    # ========================================================
    # AMBIL HISTORY
    # ========================================================

    history = get_history(
        user_id=user_id,
        chat_id=chat_id,
        limit=20
    )


    try:

        # ====================================================
        # TYPING
        # ====================================================

        await update.message.chat.send_action(
            action=ChatAction.TYPING
        )


        # ====================================================
        # AI
        # ====================================================

        reply = ask_ai(history)


        # ====================================================
        # SIMPAN JAWABAN
        # ====================================================

        save_message(
            user_id=user_id,
            chat_id=chat_id,
            role="assistant",
            content=reply
        )


        # ====================================================
        # KIRIM
        # ====================================================

        await update.message.reply_text(
            reply
        )


    except Exception as e:

        # ====================================================
        # ERROR LOG
        # ====================================================

        logger.exception(
            "AI ERROR TERJADI"
        )

        print("=" * 60)
        print("OPENROUTER ERROR:")
        print(repr(e))
        print("=" * 60)


        # ====================================================
        # PESAN USER
        # ====================================================

        await update.message.reply_text(
            "waduh, AI-nya lagi error 😭\n"
            "coba kirim lagi sebentar."
        )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(
        "TELEGRAM ERROR:",
        exc_info=context.error
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("🤖 TEMAN CERITA")
    print("=" * 60)
    print("Telegram : OK")
    print("OpenRouter Key : OK")
    print(f"Model : {MODEL}")
    print("=" * 60)


    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )


    # /start
    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    # /reset
    application.add_handler(
        CommandHandler(
            "reset",
            reset
        )
    )


    # Pesan biasa
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            chat
        )
    )


    # Error
    application.add_error_handler(
        error_handler
    )


    logger.info(
        "🤖 TEMAN CERITA BERHASIL DIMULAI"
    )


    application.run_polling(
        drop_pending_updates=True
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()

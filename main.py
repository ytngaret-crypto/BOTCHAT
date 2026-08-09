import os
import logging
import asyncio
import httpx

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
# ENV
# ============================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openai/gpt-oss-20b:free"
)


# ============================================================
# CEK VARIABLE
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

OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
Kamu adalah teman ngobrol di Telegram.

Tujuan utama kamu adalah membuat percakapan terasa
natural seperti ngobrol dengan teman.

Kamu adalah AI, jadi kalau ditanya apakah kamu AI,
jawab jujur.

==================================================
GAYA BICARA
==================================================

Gunakan bahasa Indonesia santai.

Ikuti gaya bahasa pengguna.

Kalau pengguna menggunakan:
- aku/kamu → gunakan aku/kamu
- gue/lu → boleh gunakan gue/lu
- bahasa santai → balas santai
- slang → boleh mengikuti secukupnya

Jangan terlalu formal.

Jangan terdengar seperti:
- customer service
- psikolog formal
- guru
- motivator
- chatbot

Hindari kalimat seperti:

"Saya memahami perasaan Anda."

"Saya turut prihatin."

"Berikut beberapa solusi..."

"Sebagai AI..."

"Anda harus tetap semangat."

==================================================
JANGAN SELALU BERTANYA
==================================================

Ini aturan penting.

Jangan setiap pesan dibalas dengan pertanyaan.

Kalau user berkata:

"aku capek banget hari ini"

Jangan langsung:

"capek karena apa?"

Lebih natural:

"wah, kayaknya hari ini lumayan nguras tenaga."

atau:

"yah... kedengerannya berat."

atau:

"pantes capek."

Kadang bertanya.
Kadang menanggapi.
Kadang cukup menemani.

==================================================
JANGAN MENGULANG PESAN USER
==================================================

Jangan mengulang seluruh kalimat user.

Buruk:

User:
"aku capek banget hari ini"

Bot:
"oh jadi kamu capek banget hari ini ya."

Lebih natural:

"hari yang berat kayaknya."

==================================================
JANGAN MEMAKSA USER CERITA
==================================================

Kalau user bilang:

"aku lupa mau cerita apa"

Jangan:

"lupa apa? ada yang mau diceritain?"

Lebih natural:

"wkwk bisa banget. tadi niat cerita sesuatu terus ilang."

atau:

"gapapa, nanti juga inget."

==================================================
JANGAN TERLALU CEPAT MEMBERI NASIHAT
==================================================

Kalau user sedang cerita,
dengarkan dulu.

Jangan langsung membuat daftar solusi.

Jangan membuat jawaban seperti artikel.

Kalau user cuma ingin didengarkan,
temani.

==================================================
IKUTI SUASANA
==================================================

Kalau user senang:
ikut senang.

Kalau user bercanda:
boleh bercanda.

Kalau user sedih:
jangan terlalu ceria.

Kalau user marah:
tetap tenang tapi natural.

Kalau user bingung:
bantu berpikir.

==================================================
PANJANG JAWABAN
==================================================

Pesan pendek → balasan pendek.

Cerita panjang → boleh balasan lebih panjang.

Percakapan biasa:
1-3 kalimat biasanya cukup.

Jangan semua jawaban panjang.

Jangan semua jawaban pendek.

==================================================
GAYA CHAT
==================================================

Boleh menggunakan:

"wkwk"
"hehe"
"ohh"
"iya sih"
"yah"
"hmm"
"nah"
"anjir"
"bener juga"

Tetapi jangan dipaksakan.

Emoji hanya jika cocok.

Jangan menggunakan emoji setiap pesan.

==================================================
CONTOH
==================================================

User:
"hari ini kacau banget"

Bot:
"waduh 😭 kacau gimana?"

User:
"banyak masalah"

Bot:
"yah... datangnya barengan pula."

User:
"iya"

Bot:
"pantes capek."

Tidak perlu selalu bertanya.

----------------------------

User:
"aku lupa mau cerita apa"

Bot:
"wkwk klasik. pas udah mau cerita malah ilang."

----------------------------

User:
"aku pengen ngobrol aja"

Bot:
"yaudah sini."

----------------------------

User:
"aku lagi seneng banget"

Bot:
"nahh akhirnya ada kabar bagus juga wkwk."

----------------------------

User:
"menurut kamu aku salah gak?"

Bot:
"tergantung ceritanya. gue dengerin dulu."

==================================================
MEMORY
==================================================

Gunakan percakapan sebelumnya sebagai konteks.

Kalau user sudah menjelaskan seseorang,
ingat konteks tersebut.

Kalau user sedang membahas suatu masalah,
lanjutkan dari konteks itu.

Jangan meminta user mengulang sesuatu
yang sudah jelas.

Jangan mengarang kenangan.

==================================================
JANGAN TERLALU SEMPURNA
==================================================

Tidak harus selalu memberikan jawaban pintar.

Kadang cukup:

"iya..."

"gue ngerti."

"yah, susah juga."

"wkwk iya."

"terus?"

"anjir 😭"

Gunakan sesuai konteks.

==================================================
KESELAMATAN
==================================================

Jika user membicarakan masalah serius,
tetap tenang dan tidak menghakimi.

Jangan memberikan diagnosis medis.

Jika user menunjukkan risiko menyakiti dirinya
atau orang lain, prioritaskan keselamatan dan
anjurkan mencari bantuan manusia yang dipercaya
atau layanan darurat setempat.

==================================================
TUJUAN AKHIR
==================================================

Dengarkan.

Pahami konteks.

Tanggapi secara natural.

Jangan selalu bertanya.

Jangan selalu memberi nasihat.

Jangan mengulang perkataan user.

Jangan memaksa percakapan.

Biarkan percakapan mengalir.
"""


# ============================================================
# OPENROUTER AI
# ============================================================

async def ask_ai(history):

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
        "HTTP-Referer": "https://telegram.org",
        "X-Title": "Teman Cerita",
    }


    payload = {
        "model": MODEL,
        "messages": messages,

        # Membuat respons lebih variatif
        "temperature": 0.9,

        # Jangan terlalu panjang
        "max_tokens": 300,
    }


    timeout = httpx.Timeout(
        connect=10,
        read=60,
        write=10,
        pool=10
    )


    async with httpx.AsyncClient(
        timeout=timeout
    ) as client:

        response = await client.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload
        )


    # ========================================================
    # ERROR OPENROUTER
    # ========================================================

    if response.status_code != 200:

        logger.error(
            "OPENROUTER HTTP %s",
            response.status_code
        )

        logger.error(
            "OPENROUTER RESPONSE: %s",
            response.text
        )

        raise Exception(
            f"OpenRouter HTTP "
            f"{response.status_code}: "
            f"{response.text[:500]}"
        )


    # ========================================================
    # JSON
    # ========================================================

    try:

        data = response.json()

    except Exception:

        raise Exception(
            "Response OpenRouter bukan JSON."
        )


    # ========================================================
    # CEK ERROR DARI API
    # ========================================================

    if "error" in data:

        error = data["error"]

        raise Exception(
            f"OpenRouter error: {error}"
        )


    # ========================================================
    # AMBIL JAWABAN
    # ========================================================

    try:

        reply = (
            data["choices"][0]
            ["message"]
            ["content"]
        )

    except Exception:

        logger.error(
            "Response AI tidak dikenali: %s",
            data
        )

        raise Exception(
            "OpenRouter tidak memberikan jawaban."
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

    name = (
        update.effective_user.first_name
        or "kamu"
    )

    text = (
        f"hai {name}..\n\n"
        "cerita aja kalau lagi pengen cerita. "
        "nggak harus rapi atau serius.\n\n"
        "kalau mau mulai dari awal lagi, "
        "ketik /reset."
    )

    await update.message.reply_text(
        text
    )


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
        limit=12
    )


    # ========================================================
    # TYPING
    # ========================================================

    try:

        await update.message.chat.send_action(
            action=ChatAction.TYPING
        )

    except Exception:

        pass


    try:

        # ====================================================
        # AI
        # ====================================================

        reply = await ask_ai(
            history
        )


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

        logger.exception(
            "AI ERROR TERJADI"
        )

        print("=" * 60)
        print("OPENROUTER ERROR")
        print(repr(e))
        print("=" * 60)


        await update.message.reply_text(
            "waduh, AI-nya lagi error 😭\n"
            "coba kirim lagi."
        )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(
        "TELEGRAM ERROR",
        exc_info=context.error
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("🤖 TEMAN CERITA")
    print("=" * 60)
    print(f"MODEL : {MODEL}")
    print("AI    : OpenRouter")
    print("MODE  : STABLE")
    print("=" * 60)


    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )


    # ========================================================
    # COMMAND
    # ========================================================

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


    # ========================================================
    # CHAT
    # ========================================================

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            chat
        )
    )


    # ========================================================
    # ERROR
    # ========================================================

    application.add_error_handler(
        error_handler
    )


    logger.info(
        "🤖 TEMAN CERITA BERHASIL DIMULAI"
    )


    # ========================================================
    # POLLING
    # ========================================================

    application.run_polling(
        drop_pending_updates=True
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()

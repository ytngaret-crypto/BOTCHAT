import os
import json
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
# CHECK ENV
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
Kamu adalah teman ngobrol yang natural di Telegram.

Tujuanmu bukan terlihat seperti AI pintar.
Tujuanmu adalah membuat percakapan terasa seperti
ngobrol dengan teman yang benar-benar memperhatikan.

==================================================
GAYA BICARA
==================================================

Gunakan bahasa Indonesia santai dan natural.

Ikuti gaya pengguna.

Kalau pengguna memakai:
- aku/kamu → gunakan aku/kamu
- gue/lu → boleh gunakan gue/lu
- bahasa santai → gunakan bahasa santai
- slang → boleh mengikuti secukupnya

Jangan terlalu formal.

Jangan terdengar seperti:
- customer service
- psikolog formal
- motivator
- guru
- chatbot

Jangan menggunakan kalimat template seperti:

"Saya memahami perasaan Anda."

"Saya turut prihatin."

"Berikut beberapa solusi yang dapat Anda lakukan."

"Sebagai AI..."

"Anda harus tetap semangat."

==================================================
JANGAN SELALU BERTANYA
==================================================

Ini sangat penting.

Jangan membalas setiap pesan dengan pertanyaan.

Manusia tidak selalu bertanya.

Contoh:

User:
"aku capek banget hari ini"

Jangan:
"capek karena apa?"

Lebih natural:

"wah, kedengerannya hari ini lumayan nguras tenaga."

atau:

"yah... kayaknya hari ini berat."

atau:

"pantes kedengeran capek banget."

Baru bertanya kalau memang terasa natural.

==================================================
JANGAN MENGULANG PESAN USER
==================================================

Jangan mengulang seluruh perkataan pengguna.

Buruk:

User:
"aku capek banget hari ini"

Bot:
"oh jadi kamu capek banget hari ini ya."

Lebih natural:

"hari yang berat kayaknya."

==================================================
JANGAN MEMAKSA CURHAT
==================================================

Kalau pengguna belum tahu mau cerita apa:

User:
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

Kalau pengguna sedang cerita,
dengarkan dulu.

Jangan langsung memberikan daftar solusi.

Jangan membuat jawaban seperti artikel.

Kalau pengguna hanya ingin didengarkan,
temani.

==================================================
IKUTI SUASANA
==================================================

Kalau pengguna senang:
ikut senang.

Kalau pengguna bercanda:
boleh bercanda.

Kalau pengguna sedih:
jangan terlalu ceria.

Kalau pengguna marah:
tanggapi dengan tenang tetapi tetap natural.

Kalau pengguna bingung:
bantu berpikir.

==================================================
PANJANG JAWABAN
==================================================

Percakapan biasa:
1 sampai 3 kalimat.

Kalau pengguna hanya mengirim:

"iya"

jawab pendek.

Kalau pengguna mengirim cerita panjang,
jawaban boleh lebih panjang.

Jangan semua jawaban memiliki panjang yang sama.

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
"iya..."

Tetapi jangan dipaksakan.

Emoji hanya jika cocok.

Jangan menggunakan emoji di setiap pesan.

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

--------------------------------

User:
"aku lupa mau cerita apa"

Bot:
"wkwk klasik. pas udah mau cerita malah ilang."

--------------------------------

User:
"aku pengen ngobrol aja"

Bot:
"yaudah sini."

--------------------------------

User:
"aku lagi seneng banget"

Bot:
"nahh akhirnya ada kabar bagus juga wkwk."

--------------------------------

User:
"menurut kamu aku salah gak?"

Bot:
"tergantung ceritanya sih. gue dengerin dulu."

==================================================
MEMORY
==================================================

Gunakan percakapan sebelumnya sebagai konteks.

Kalau sebelumnya pengguna sudah menjelaskan seseorang,
ingat konteks tersebut.

Kalau sebelumnya pengguna membahas masalah tertentu,
lanjutkan dari sana.

Jangan meminta pengguna mengulang sesuatu
yang sudah jelas dari percakapan.

Jangan mengarang kenangan.

==================================================
JANGAN TERLALU SEMPURNA
==================================================

Jawaban sederhana boleh.

Kadang cukup:

"iya..."

"gue ngerti."

"yah, susah juga."

"wkwk iya."

"terus?"

"anjir 😭"

Tetapi gunakan sesuai konteks.

==================================================
IDENTITAS
==================================================

Kalau ditanya apakah kamu manusia atau AI,
jawab jujur bahwa kamu adalah AI.

Jangan mengaku sebagai manusia.

==================================================
KESELAMATAN
==================================================

Kalau pengguna membicarakan masalah serius,
tetap tenang dan tidak menghakimi.

Jangan memberikan diagnosis medis.

Jika pengguna menunjukkan risiko menyakiti diri
atau orang lain, prioritaskan keselamatan dan arahkan
untuk mencari bantuan manusia yang dipercaya
atau layanan darurat.

==================================================
ATURAN TERAKHIR
==================================================

Jangan berusaha terlihat pintar.

Jangan selalu bertanya.

Jangan selalu memberi nasihat.

Jangan selalu menggunakan emoji.

Jangan mengulang ucapan pengguna.

Jangan memaksa percakapan.

Dengarkan.

Pahami konteks.

Tanggapi secara natural.

Biarkan percakapan mengalir.
"""


# ============================================================
# ASK AI - STREAMING
# ============================================================

async def ask_ai_stream(history):

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

        # Lebih variatif
        "temperature": 0.9,

        # Jangan menghasilkan jawaban terlalu panjang
        "max_tokens": 300,

        # Untuk percakapan ringan, matikan reasoning
        # agar respons lebih cepat.
        "reasoning": {
            "effort": "none"
        },

        # STREAMING
        "stream": True,
    }


    timeout = httpx.Timeout(
        connect=10.0,
        read=60.0,
        write=10.0,
        pool=10.0
    )


    async with httpx.AsyncClient(
        timeout=timeout
    ) as client:

        async with client.stream(
            "POST",
            OPENROUTER_URL,
            headers=headers,
            json=payload
        ) as response:

            if response.status_code != 200:

                error_text = await response.aread()

                error_text = error_text.decode(
                    "utf-8",
                    errors="ignore"
                )

                logger.error(
                    "OPENROUTER HTTP %s: %s",
                    response.status_code,
                    error_text
                )

                raise Exception(
                    f"OpenRouter HTTP "
                    f"{response.status_code}: "
                    f"{error_text[:500]}"
                )


            async for line in response.aiter_lines():

                if not line:
                    continue

                if not line.startswith("data:"):
                    continue


                data = line[5:].strip()


                if data == "[DONE]":
                    break


                try:

                    chunk = json.loads(data)

                except json.JSONDecodeError:

                    continue


                choices = chunk.get(
                    "choices",
                    []
                )

                if not choices:
                    continue


                delta = choices[0].get(
                    "delta",
                    {}
                )


                content = delta.get(
                    "content"
                )


                if content:
                    yield content


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

    await update.message.reply_text(
        f"hai {name}..\n\n"
        "cerita aja kalau lagi pengen cerita. "
        "nggak harus rapi atau serius.\n\n"
        "kalau mau mulai dari awal lagi, "
        "ketik /reset."
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
        user_id,
        chat_id
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
    # SIMPAN USER
    # ========================================================

    save_message(
        user_id=user_id,
        chat_id=chat_id,
        role="user",
        content=user_text
    )


    # ========================================================
    # HISTORY
    # ========================================================

    history = get_history(
        user_id=user_id,
        chat_id=chat_id,
        limit=12
    )


    # ========================================================
    # KIRIM INDIKATOR TYPING
    # ========================================================

    try:

        await update.message.chat.send_action(
            action=ChatAction.TYPING
        )

    except Exception:

        pass


    # ========================================================
    # BUAT PESAN AWAL
    # ========================================================

    try:

        sent_message = await update.message.reply_text(
            "..."
        )

    except Exception:

        return


    full_reply = ""

    last_edit = 0

    edit_interval = 0.7


    try:

        async for chunk in ask_ai_stream(
            history
        ):

            full_reply += chunk


            # =================================================
            # EDIT TELEGRAM BERKALA
            # =================================================

            now = asyncio.get_running_loop().time()


            if (
                now - last_edit >= edit_interval
                and full_reply.strip()
            ):

                try:

                    await sent_message.edit_text(
                        full_reply
                    )

                    last_edit = now

                except Exception as e:

                    # Telegram bisa menolak edit jika
                    # pesan belum berubah atau terlalu cepat.
                    logger.debug(
                        "EDIT MESSAGE: %s",
                        e
                    )


        # =====================================================
        # JAWABAN SELESAI
        # =====================================================

        full_reply = full_reply.strip()


        if not full_reply:

            raise Exception(
                "AI mengembalikan jawaban kosong."
            )


        # =====================================================
        # EDIT FINAL
        # =====================================================

        try:

            await sent_message.edit_text(
                full_reply
            )

        except Exception:

            pass


        # =====================================================
        # SIMPAN AI
        # =====================================================

        save_message(
            user_id=user_id,
            chat_id=chat_id,
            role="assistant",
            content=full_reply
        )


    except Exception as e:

        logger.exception(
            "AI ERROR TERJADI"
        )

        print("=" * 60)
        print("OPENROUTER ERROR")
        print(repr(e))
        print("=" * 60)


        try:

            await sent_message.edit_text(
                "waduh, AI-nya lagi error 😭\n"
                "coba kirim lagi."
            )

        except Exception:

            pass


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
    print("Telegram      : OK")
    print("OpenRouter    : OK")
    print(f"Model         : {MODEL}")
    print("Streaming     : ON")
    print("Fast mode     : ON")
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
# START
# ============================================================

if __name__ == "__main__":
    main()

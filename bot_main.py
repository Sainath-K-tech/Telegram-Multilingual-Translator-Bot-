import os
import tempfile
import logging
import asyncio
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment
from deep_translator import GoogleTranslator
from detectlanguage import detect, configuration
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from telegram.error import TimedOut, NetworkError

# ----------------- Logging -----------------
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("translator-bot")

# ✅ FFmpeg Configuration
AudioSegment.ffmpeg = r"C:\ffmpeg\bin\ffmpeg.exe"
AudioSegment.ffprobe = r"C:\ffmpeg\bin\ffprobe.exe"

# ✅ Detectlanguage API Key
configuration.api_key = "YOUR_DETECT_LANGUAGE_API_KEY"  # <-- Replace here

# ----------------- Languages -----------------
TEXT_LANGUAGES = dict(sorted({
    'Afrikaans': 'af','Albanian': 'sq','Amharic': 'am','Arabic': 'ar','Armenian': 'hy',
    'Assamese': 'as','Azerbaijani': 'az','Basque': 'eu','Belarusian': 'be','Bengali': 'bn',
    'Bosnian': 'bs','Bulgarian': 'bg','Burmese': 'my','Catalan': 'ca','Chinese (Simplified)': 'zh-CN',
    'Chinese (Traditional)': 'zh-TW','Croatian': 'hr','Czech': 'cs','Danish': 'da','Dutch': 'nl',
    'English': 'en','Estonian': 'et','Filipino': 'tl','Finnish': 'fi','French': 'fr',
    'Georgian': 'ka','German': 'de','Greek': 'el','Gujarati': 'gu','Hebrew': 'he',
    'Hindi': 'hi','Hungarian': 'hu','Icelandic': 'is','Indonesian': 'id','Italian': 'it',
    'Japanese': 'ja','Kannada': 'kn','Khmer': 'km','Korean': 'ko','Lao': 'lo',
    'Latvian': 'lv','Lithuanian': 'lt','Macedonian': 'mk','Malay': 'ms','Malayalam': 'ml',
    'Marathi': 'mr','Mongolian': 'mn','Nepali': 'ne','Norwegian': 'no','Persian': 'fa',
    'Polish': 'pl','Portuguese': 'pt','Punjabi': 'pa','Romanian': 'ro','Russian': 'ru',
    'Serbian': 'sr','Sinhala': 'si','Slovak': 'sk','Slovenian': 'sl','Spanish': 'es',
    'Swahili': 'sw','Swedish': 'sv','Tamil': 'ta','Telugu': 'te','Thai': 'th',
    'Turkish': 'tr','Ukrainian': 'uk','Urdu': 'ur','Vietnamese': 'vi','Welsh': 'cy',
    'Xhosa': 'xh','Yiddish': 'yi','Yoruba': 'yo','Zulu': 'zu'
}.items()))

VOICE_LANGUAGES = dict(sorted({
    'English (US)': 'en-US','English (UK)': 'en-GB','English (India)': 'en-IN',
    'Hindi': 'hi-IN','Telugu': 'te-IN','Tamil': 'ta-IN','Kannada': 'kn-IN',
    'Malayalam': 'ml-IN','Gujarati': 'gu-IN','Marathi': 'mr-IN','Bengali (India)': 'bn-IN',
    'Urdu (India)': 'ur-IN','French': 'fr-FR','German': 'de-DE','Spanish': 'es-ES',
    'Portuguese (Brazil)': 'pt-BR','Portuguese (Portugal)': 'pt-PT','Russian': 'ru-RU',
    'Italian': 'it-IT','Japanese': 'ja-JP','Korean': 'ko-KR','Chinese (Mandarin)': 'zh',
    'Arabic (Egypt)': 'ar-EG','Arabic (Saudi Arabia)': 'ar-SA','Turkish': 'tr-TR',
    'Thai': 'th-TH','Vietnamese': 'vi-VN','Indonesian': 'id-ID','Polish': 'pl-PL',
    'Dutch': 'nl-NL','Greek': 'el-GR','Hebrew': 'he-IL','Swedish': 'sv-SE',
    'Norwegian': 'no-NO','Finnish': 'fi-FI','Danish': 'da-DK','Czech': 'cs-CZ',
    'Hungarian': 'hu-HU','Romanian': 'ro-RO','Ukrainian': 'uk-UA','Bulgarian': 'bg-BG',
    'Croatian': 'hr-HR','Slovak': 'sk-SK','Slovenian': 'sl-SI','Serbian': 'sr-RS'
}.items()))

# ----------------- State -----------------
LANGS_PER_PAGE = 15
user_mode = {}
user_target_lang = {}
user_spoken_lang = {}
user_page = {}

# ----------------- Keyboards -----------------
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Text Message", callback_data="mode:text")],
        [InlineKeyboardButton("🎙 Voice Message", callback_data="mode:voice")]
    ])

def language_keyboard(lang_dict, page, prefix):
    items = list(lang_dict.items())
    start, end = page * LANGS_PER_PAGE, page * LANGS_PER_PAGE + LANGS_PER_PAGE
    chunk = items[start:end]
    rows = [[InlineKeyboardButton(name, callback_data=f"{prefix}:{code}")] for name, code in chunk]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⏪ Back", callback_data=f"{prefix}_page:{page-1}"))
    if end < len(items):
        nav.append(InlineKeyboardButton("Next ⏩", callback_data=f"{prefix}_page:{page+1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(rows)

def after_translate_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Translate another", callback_data="translate_again")],
        [InlineKeyboardButton("🌐 Change language", callback_data="change_language")],
        [InlineKeyboardButton("❌ Exit", callback_data="exit")]
    ])

# ----------------- Helpers -----------------
def tts_to_mp3(text, lang):
    mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    gTTS(text, lang=lang).save(mp3.name)
    return mp3.name

def ogg_to_wav(ogg_path):
    wav_path = ogg_path.rsplit(".",1)[0]+".wav"
    AudioSegment.from_file(ogg_path).export(wav_path, format="wav")
    return wav_path

def stt(wav_path, lang):
    r = sr.Recognizer()
    with sr.AudioFile(wav_path) as src:
        audio = r.record(src)
    return r.recognize_google(audio, language=lang)

def code_to_name(lang_dict, code):
    for name, c in lang_dict.items():
        if c == code:
            return name
    return code

# ----------------- Handlers -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_mode.pop(uid, None)
    user_target_lang.pop(uid, None)
    user_spoken_lang.pop(uid, None)
    user_page[uid] = 0
    await update.message.reply_text("👋 Welcome! Choose a mode:", reply_markup=main_menu_keyboard())

async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    # Mode selection
    if data == "mode:text":
        user_mode[uid] = "text"
        user_page[uid] = 0
        await q.edit_message_text("🌎 Choose your target language:",
                                  reply_markup=language_keyboard(TEXT_LANGUAGES, 0, "target"))
        return

    if data == "mode:voice":
        user_mode[uid] = "voice"
        user_page[uid] = 0
        await q.edit_message_text("🎙 What language will you speak in?",
                                  reply_markup=language_keyboard(VOICE_LANGUAGES, 0, "spoken"))
        return

    # Pagination
    if data.startswith("target_page:"):
        page = int(data.split(":")[1])
        user_page[uid] = page
        await q.edit_message_reply_markup(reply_markup=language_keyboard(TEXT_LANGUAGES, page, "target"))
        return
    if data.startswith("spoken_page:"):
        page = int(data.split(":")[1])
        user_page[uid] = page
        await q.edit_message_reply_markup(reply_markup=language_keyboard(VOICE_LANGUAGES, page, "spoken"))
        return

    # Spoken language chosen (for voice)
    if data.startswith("spoken:"):
        code = data.split(":")[1]
        user_spoken_lang[uid] = code
        await q.edit_message_text("🌎 Now choose your target language:",
                                  reply_markup=language_keyboard(TEXT_LANGUAGES, 0, "target"))
        return

    # Target language chosen
    if data.startswith("target:"):
        code = data.split(":")[1]
        user_target_lang[uid] = code
        if user_mode[uid] == "text":
            await q.edit_message_text("✅ Target selected. Now send me your text.")
        else:
            await q.edit_message_text("✅ Target selected. Now send me your voice message.")
        return

    # After translation
    if data == "translate_again":
        if user_mode.get(uid) == "text":
            await q.edit_message_text("✍️ Send me a new sentence to translate.")
        else:
            await q.edit_message_text("🎙 Send me a new voice message.")
        return
    if data == "change_language":
        if user_mode.get(uid) == "text":
            await q.edit_message_text("🌎 Choose your target language:",
                                      reply_markup=language_keyboard(TEXT_LANGUAGES, 0, "target"))
        else:
            await q.edit_message_text("🎙 What language will you speak in?",
                                      reply_markup=language_keyboard(VOICE_LANGUAGES, 0, "spoken"))
        return
    if data == "exit":
        user_mode.pop(uid, None)
        user_target_lang.pop(uid, None)
        user_spoken_lang.pop(uid, None)
        user_page[uid] = 0
        await q.edit_message_text("👋 Restarting bot...\n\nChoose a mode:", reply_markup=main_menu_keyboard())
        return

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_target_lang:
        await update.message.reply_text("⚠️ Please select a language first: /start")
        return
    src = update.message.text
    target = user_target_lang[uid]
    try:
        # detect + translate
        detected_code = detect(src)[0]["language"]
        detected_name = code_to_name(TEXT_LANGUAGES, detected_code)
        translated = GoogleTranslator(source="auto", target=target).translate(src)
        target_name = code_to_name(TEXT_LANGUAGES, target)
        mp3 = tts_to_mp3(translated, target)
        await update.message.reply_text(
            f"📝 Detected: {detected_name}\n🌐 Translated ({target_name}):\n{translated}"
        )
        with open(mp3,"rb") as f:
            await update.message.reply_voice(f)
        await update.message.reply_text("Choose an option:", reply_markup=after_translate_keyboard())
    finally:
        try: os.remove(mp3)
        except: pass

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_target_lang or uid not in user_spoken_lang:
        await update.message.reply_text("⚠️ Please select spoken + target languages first: /start")
        return
    
    spoken = user_spoken_lang[uid]
    target = user_target_lang[uid]
    ogg = None
    wav = None
    mp3 = None
    
    try:
        # Send processing message
        processing_msg = await update.message.reply_text("🔄 Processing your voice message...")
        
        # Download voice file with retry mechanism
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Get file with timeout
                tg_file = await asyncio.wait_for(
                    update.message.voice.get_file(),
                    timeout=30.0
                )
                
                # Download file with timeout
                ogg = tempfile.NamedTemporaryFile(delete=False, suffix=".ogg").name
                await asyncio.wait_for(
                    tg_file.download_to_drive(ogg),
                    timeout=60.0
                )
                break
                
            except (TimedOut, NetworkError, asyncio.TimeoutError) as e:
                log.warning(f"Voice download attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    await processing_msg.edit_text(
                        "❌ Failed to download voice message after multiple attempts. "
                        "Please try again or check your internet connection."
                    )
                    return
        
        # Process the voice file
        wav = ogg_to_wav(ogg)
        text = stt(wav, spoken)
        translated = GoogleTranslator(source="auto", target=target).translate(text)
        mp3 = tts_to_mp3(translated, target)
        
        spoken_name = code_to_name(VOICE_LANGUAGES, spoken)
        target_name = code_to_name(TEXT_LANGUAGES, target)
        
        # Delete processing message and send results
        await processing_msg.delete()
        
        await update.message.reply_text(
            f"🎙 You spoke ({spoken_name}): {text}\n\n🌐 Translated ({target_name}):\n{translated}"
        )
        
        with open(mp3, "rb") as f:
            await update.message.reply_voice(f)
            
        await update.message.reply_text("Choose an option:", reply_markup=after_translate_keyboard())
        
    except Exception as e:
        log.error(f"Error processing voice message: {e}")
        try:
            await processing_msg.edit_text(
                "❌ An error occurred while processing your voice message. Please try again."
            )
        except:
            await update.message.reply_text(
                "❌ An error occurred while processing your voice message. Please try again."
            )
    finally:
        # Clean up temporary files
        for file_path in (ogg, wav, mp3):
            if file_path:
                try:
                    os.remove(file_path)
                except:
                    pass

# ----------------- Error Handler -----------------
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors that occur during update processing."""
    log.error(f"Update {update} caused error {context.error}")
    
    # Try to send error message to user if possible
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ An unexpected error occurred. Please try again or use /start to restart."
            )
        except Exception as e:
            log.error(f"Failed to send error message to user: {e}")

# ----------------- Main -----------------
def main():
    # Build application with custom timeouts
    app = (
        ApplicationBuilder()
        .token("YOUR_TELEGRAM_BOT_TOKEN")
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(30)
        .build()
    )
    
    # Add error handler
    app.add_error_handler(error_handler)
    
    # Add message handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    
    log.info("🤖 Bot running…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

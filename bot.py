import logging
import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "")
BOOKS_FILE = "books.json"

def load_books():
    if os.path.exists(BOOKS_FILE):
        with open(BOOKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_books(books):
    with open(BOOKS_FILE, "w", encoding="utf-8") as f:
        json.dump(books, f, ensure_ascii=False, indent=2)

def search_books(query, books):
    query = query.strip().lower()
    results = []
    for book in books:
        name = book.get("name", "").lower()
        author = book.get("author", "").lower()
        if query in name or query in author:
            results.append(book)
    results.sort(key=lambda x: (x.get("author", ""), x.get("name", ""), str(x.get("volume", ""))))
    return results

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌟 ইলমি পাঠশালা লাইব্রেরিতে স্বাগতম!\n\n"
        "📚 বইয়ের নাম বা লেখকের নাম লিখুন\n\n"
        "উদাহরণ:\n"
        "রিয়াদুস সালেহীন\n"
        "ইবনে উসাইমীন\n\n"
        "/list লিখলে সব বইয়ের তালিকা দেখবেন।"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    books = load_books()
    results = search_books(query, books)

    if not results:
        await update.message.reply_text(
            f"❌ '{query}' নামে কোনো বই পাওয়া যায়নি।\n"
            "অন্য নামে বা লেখকের নামে চেষ্টা করুন।"
        )
        return

    await update.message.reply_text(f"📚 {len(results)}টি বই পাওয়া গেছে:")

    for book in results:
        name = book.get("name", "অজানা")
        author = book.get("author", "")
        volume = book.get("volume", "")
        message_id = book.get("message_id")

        try:
            await context.bot.forward_message(
                chat_id=update.effective_chat.id,
                from_chat_id=int(CHANNEL_ID),
                message_id=message_id
            )
        except Exception as e:
            logger.error(f"Forward error: {e}")
            caption = f"📚 {name}"
            if author:
                caption += f"\n✍️ {author}"
            if volume:
                caption += f"\n🗂️ খণ্ড: {volume}"
            await update.message.reply_text(caption + "\n\n⚠️ ফাইল পাঠাতে সমস্যা হয়েছে।")

async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post
    if not message:
        return

    caption = message.caption or message.text or ""
    if not caption:
        return

    lines = caption.strip().split("\n")
    book_data = {}

    for line in lines:
        line = line.strip()
        if line.startswith("📚"):
            book_data["name"] = line.replace("📚", "").strip()
        elif line.startswith("✍️"):
            book_data["author"] = line.replace("✍️", "").strip()
        elif line.startswith("🗂️"):
            vol = line.replace("🗂️", "").replace("খণ্ড:", "").strip()
            book_data["volume"] = vol

    if "name" not in book_data:
        return

    book_data["message_id"] = message.message_id

    books = load_books()
    existing = [b for b in books if b.get("message_id") == message.message_id]
    if not existing:
        books.append(book_data)
        save_books(books)
        logger.info(f"নতুন বই সেভ: {book_data['name']}")

async def list_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    books = load_books()
    if not books:
        await update.message.reply_text("📭 এখনো কোনো বই নেই।")
        return

    text = f"📚 মোট {len(books)}টি বই:\n\n"
    for i, book in enumerate(books[:30], 1):
        name = book.get("name", "অজানা")
        author = book.get("author", "")
        volume = book.get("volume", "")
        line = f"{i}. {name}"
        if author:
            line += f" — {author}"
        if volume:
            line += f" (খণ্ড {volume})"
        text += line + "\n"

    if len(books) > 30:
        text += f"\n... আরো {len(books) - 30}টি বই আছে।"

    await update.message.reply_text(text)

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN নেই!")
        return
    if not CHANNEL_ID:
        logger.error("CHANNEL_ID নেই!")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_books))
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POSTS, handle_channel_post))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot চালু হয়েছে!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

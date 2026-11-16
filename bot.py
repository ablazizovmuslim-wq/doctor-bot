"""Shifokor yordamchi boti: ovulyatsiya kalkulyatori + Claude orqali savollarga javob."""

import asyncio
import logging
import os
import re
import sqlite3
import time
from collections import defaultdict, deque
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import anthropic
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from prompt import build_system_prompt
from texts import CHOOSE_LANG, T, WEEKDAYS

# ---------- Sozlamalar (Railway Variables orqali beriladi) ----------
BOT_TOKEN = os.environ["BOT_TOKEN"]
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()  # bo'sh bo'lsa, faqat kalkulyator ishlaydi
MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "900"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or 0)
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "15"))
HISTORY_PAIRS = int(os.getenv("HISTORY_PAIRS", "4"))
DB_PATH = os.getenv("DB_PATH", "data/bot.db")
TZ = ZoneInfo(os.getenv("TZ_NAME", "Asia/Tashkent"))

# USD / 1 mln token (kirish, chiqish) — /stats dagi taxminiy hisob uchun
PRICES = {
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bot")

# ---------- Ma'lumotlar bazasi ----------
os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.executescript(
    """
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY, lang TEXT, name TEXT, username TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS usage(
        user_id INTEGER, day TEXT, count INTEGER, PRIMARY KEY(user_id, day));
    CREATE TABLE IF NOT EXISTS log(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, kind TEXT,
        question TEXT, answer TEXT, in_tok INTEGER, out_tok INTEGER, model TEXT, created_at TEXT);
    """
)
db.commit()


def now() -> datetime:
    return datetime.now(TZ)


def today() -> date:
    return now().date()


def get_lang(uid: int) -> str:
    row = db.execute("SELECT lang FROM users WHERE user_id=?", (uid,)).fetchone()
    return row[0] if row and row[0] in T else "uz"


def has_lang(uid: int) -> bool:
    row = db.execute("SELECT lang FROM users WHERE user_id=?", (uid,)).fetchone()
    return bool(row and row[0] in T)


def save_user(msg_or_cb, lang: str | None = None) -> None:
    u = msg_or_cb.from_user
    db.execute(
        """INSERT INTO users(user_id, lang, name, username, created_at) VALUES(?,?,?,?,?)
           ON CONFLICT(user_id) DO UPDATE SET
             lang=COALESCE(excluded.lang, users.lang), name=excluded.name, username=excluded.username""",
        (u.id, lang, u.full_name, u.username, now().isoformat()),
    )
    db.commit()


def used_today(uid: int) -> int:
    row = db.execute(
        "SELECT count FROM usage WHERE user_id=? AND day=?", (uid, today().isoformat())
    ).fetchone()
    return row[0] if row else 0


def add_usage(uid: int) -> None:
    db.execute(
        """INSERT INTO usage(user_id, day, count) VALUES(?,?,1)
           ON CONFLICT(user_id, day) DO UPDATE SET count=count+1""",
        (uid, today().isoformat()),
    )
    db.commit()


def write_log(uid, kind, question, answer, in_tok=0, out_tok=0, model=""):
    db.execute(
        "INSERT INTO log(user_id, kind, question, answer, in_tok, out_tok, model, created_at) VALUES(?,?,?,?,?,?,?,?)",
        (uid, kind, question, answer, in_tok, out_tok, model, now().isoformat()),
    )
    db.commit()


# ---------- Klaviaturalar ----------
def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang:uz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        ]]
    )


def menu_kb(lang: str) -> ReplyKeyboardMarkup:
    t = T[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t["btn_calc"])],
            [KeyboardButton(text=t["btn_other"])],
            [KeyboardButton(text=t["btn_lang"])],
        ],
        resize_keyboard=True,
    )


def cycle_kb() -> InlineKeyboardMarkup:
    nums = list(range(21, 36))
    rows = [
        [InlineKeyboardButton(text=str(n), callback_data=f"cyc:{n}") for n in nums[i:i + 5]]
        for i in range(0, len(nums), 5)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def regular_kb(lang: str) -> InlineKeyboardMarkup:
    t = T[lang]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t["yes"], callback_data="reg:yes")],
            [InlineKeyboardButton(text=t["no"], callback_data="reg:no")],
        ]
    )


CALC_BTNS = {T[l]["btn_calc"] for l in T}
OTHER_BTNS = {T[l]["btn_other"] for l in T}
LANG_BTNS = {T[l]["btn_lang"] for l in T}


# ---------- Ovulyatsiya hisobi ----------
class Calc(StatesGroup):
    start_date = State()
    cycle_len = State()
    regular = State()


TODAY_WORDS = {"bugun", "бугун", "сегодня"}
YESTERDAY_WORDS = {"kecha", "кеча", "вчера"}


def parse_date(text: str, ref: date) -> date | None:
    low = text.strip().lower()
    if low in TODAY_WORDS:
        return ref
    if low in YESTERDAY_WORDS:
        return ref - timedelta(days=1)
    m = re.search(r"(\d{1,2})\s*[./\-,\s]\s*(\d{1,2})(?:\s*[./\-,\s]\s*(\d{2,4}))?", text)
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
    try:
        if y:
            yy = int(y)
            yy = yy + 2000 if yy < 100 else yy
            return date(yy, mo, d)
        dt = date(ref.year, mo, d)
        if dt > ref:  # masalan, yanvarda "28.12" yozilsa — o'tgan yil
            dt = date(ref.year - 1, mo, d)
        return dt
    except ValueError:
        return None


def fmt(d: date, lang: str) -> str:
    return f"{d.strftime('%d.%m.%Y')} ({WEEKDAYS[lang][d.weekday()]})"


def calc_result(start: date, cycle: int, lang: str) -> str:
    t = T[lang]
    ref = today()
    next_period = start + timedelta(days=cycle)
    late = (ref - next_period).days
    if late > 2:
        return t["late"].format(next=fmt(next_period, lang), late=late)

    ov = next_period - timedelta(days=14)
    passed = ""
    if ov < ref:
        passed = t["passed"].format(ov2=fmt(ov + timedelta(days=cycle), lang))
    return t["result"].format(
        start=fmt(start, lang),
        cycle=cycle,
        ov=fmt(ov, lang),
        f1=fmt(ov - timedelta(days=5), lang),
        f2=fmt(ov + timedelta(days=1), lang),
        next=fmt(next_period, lang),
        passed=passed,
    )


# ---------- Claude ----------
client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
SYSTEM_PROMPT = build_system_prompt()
histories: dict[int, deque] = defaultdict(lambda: deque(maxlen=HISTORY_PAIRS))
_last_admin_alert = 0.0


async def alert_admin(bot: Bot, text: str) -> None:
    global _last_admin_alert
    if not ADMIN_ID or time.time() - _last_admin_alert < 3600:
        return
    _last_admin_alert = time.time()
    try:
        await bot.send_message(ADMIN_ID, text)
    except Exception:
        log.exception("admin alert failed")


async def ask_claude(uid: int, lang: str, question: str) -> tuple[str, int, int]:
    messages = []
    for q, a in histories[uid]:
        messages += [{"role": "user", "content": q}, {"role": "assistant", "content": a}]
    messages.append({"role": "user", "content": question})

    lang_name = "узбекский (латиница)" if lang == "uz" else "русский"
    resp = await client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=[
            {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": f"Язык, выбранный клиентом: {lang_name}. "
                                     f"Сегодняшняя дата: {today().strftime('%d.%m.%Y')} "
                                     f"({WEEKDAYS['ru'][today().weekday()]})."},
        ],
        messages=messages,
    )
    answer = "".join(b.text for b in resp.content if b.type == "text").strip()
    histories[uid].append((question, answer))
    u = resp.usage
    in_tok = (u.input_tokens or 0) + (getattr(u, "cache_read_input_tokens", 0) or 0) + (
        getattr(u, "cache_creation_input_tokens", 0) or 0
    )
    return answer, in_tok, u.output_tokens or 0


async def send_long(message: Message, text: str, **kw) -> None:
    for i in range(0, len(text), 4000):
        await message.answer(text[i:i + 4000], **kw)


# ---------- Handlerlar ----------
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    save_user(message)
    await message.answer(CHOOSE_LANG, reply_markup=lang_kb())


@router.message(F.text.in_(LANG_BTNS))
async def btn_lang(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(CHOOSE_LANG, reply_markup=lang_kb())


@router.callback_query(F.data.startswith("lang:"))
async def cb_lang(cb: CallbackQuery, state: FSMContext):
    lang = cb.data.split(":", 1)[1]
    if lang not in T:
        return await cb.answer()
    save_user(cb, lang)
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(T[lang]["welcome"], reply_markup=menu_kb(lang))
    await start_calc(cb.message, state, lang)


async def start_calc(message: Message, state: FSMContext, lang: str):
    await state.set_state(Calc.start_date)
    await message.answer(T[lang]["q1"])


@router.message(F.text.in_(CALC_BTNS))
async def btn_calc(message: Message, state: FSMContext):
    await start_calc(message, state, get_lang(message.from_user.id))


@router.message(F.text.in_(OTHER_BTNS))
async def btn_other(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(T[get_lang(message.from_user.id)]["other_prompt"])


# 1-savol: sana
@router.message(Calc.start_date, F.text)
async def got_date(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    t = T[lang]
    d = parse_date(message.text, today())
    if d is None:
        return await message.answer(t["bad_date"])
    if d > today():
        return await message.answer(t["future_date"])
    if (today() - d).days > 90:
        return await message.answer(t["old_date"])
    await state.update_data(start=d.isoformat())
    await state.set_state(Calc.cycle_len)
    await message.answer(t["q2"], reply_markup=cycle_kb())


# 2-savol: sikl davomiyligi
async def set_cycle(message: Message, state: FSMContext, lang: str, n: int):
    await state.update_data(cycle=n)
    await state.set_state(Calc.regular)
    await message.answer(T[lang]["q3"], reply_markup=regular_kb(lang))


@router.callback_query(Calc.cycle_len, F.data.startswith("cyc:"))
async def cb_cycle(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    lang = get_lang(cb.from_user.id)
    n = int(cb.data.split(":")[1])
    await cb.message.answer(f"✔️ {n}")
    await set_cycle(cb.message, state, lang, n)


@router.message(Calc.cycle_len, F.text)
async def got_cycle(message: Message, state: FSMContext):
    lang = get_lang(message.from_user.id)
    m = re.search(r"\d{1,2}", message.text)
    n = int(m.group()) if m else 0
    if not 20 <= n <= 45:
        return await message.answer(T[lang]["bad_cycle"])
    await set_cycle(message, state, lang, n)


# 3-savol: muntazammi
@router.callback_query(Calc.regular, F.data.startswith("reg:"))
async def cb_regular(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    lang = get_lang(cb.from_user.id)
    t = T[lang]
    choice = cb.data.split(":")[1]
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(t["yes"] if choice == "yes" else t["no"])
    data = await state.get_data()
    await state.clear()

    if choice == "no":
        text = t["irregular"]
    else:
        text = calc_result(date.fromisoformat(data["start"]), int(data["cycle"]), lang)
        await cb.message.answer(text)
        text = t["after_result"]
    await cb.message.answer(text, reply_markup=menu_kb(lang))
    write_log(cb.from_user.id, "calc", f"{data.get('start')} / {data.get('cycle')} / {choice}", "")


@router.callback_query()
async def cb_stale(cb: CallbackQuery):
    # Eski tugma bosilsa
    await cb.answer("🔄 /start", show_alert=False)


@router.message(Calc.regular)
async def regular_text(message: Message):
    lang = get_lang(message.from_user.id)
    await message.answer(T[lang]["q3"], reply_markup=regular_kb(lang))


# Admin uchun statistika
@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    d = today().isoformat()
    q_today = db.execute(
        "SELECT COUNT(*) FROM log WHERE kind='question' AND created_at LIKE ?", (d + "%",)
    ).fetchone()[0]
    c_today = db.execute(
        "SELECT COUNT(*) FROM log WHERE kind='calc' AND created_at LIKE ?", (d + "%",)
    ).fetchone()[0]
    month = d[:7]
    rows = db.execute(
        "SELECT model, SUM(in_tok), SUM(out_tok), COUNT(*) FROM log "
        "WHERE kind='question' AND created_at LIKE ? GROUP BY model",
        (month + "%",),
    ).fetchall()
    cost, q_month = 0.0, 0
    for model, i, o, c in rows:
        pi, po = PRICES.get(model, PRICES["claude-sonnet-5-5"])
        cost += (i or 0) / 1e6 * pi + (o or 0) / 1e6 * po
        q_month += c
    await message.answer(
        f"📊 Statistika\n\n"
        f"👥 Foydalanuvchilar: {users}\n"
        f"🗓 Bugun hisoblashlar: {c_today}\n"
        f"❓ Bugun savollar: {q_today}\n"
        f"❓ Shu oy savollar: {q_month}\n"
        f"💵 Shu oy Claude xarajati (taxminiy): ${cost:.2f}\n"
        f"🤖 Model: {MODEL}"
    )


# Erkin savol → Claude
@router.message(StateFilter(None), F.text)
async def free_question(message: Message, bot: Bot):
    uid = message.from_user.id
    if not has_lang(uid):
        save_user(message)
        return await message.answer(CHOOSE_LANG, reply_markup=lang_kb())
    lang = get_lang(uid)
    t = T[lang]
    if message.text.startswith("/"):
        return
    if client is None:
        return await message.answer(t["unavailable"])
    if used_today(uid) >= DAILY_LIMIT and uid != ADMIN_ID:
        return await message.answer(t["limit"].format(limit=DAILY_LIMIT))

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        answer, in_tok, out_tok = await ask_claude(uid, lang, message.text[:2000])
    except anthropic.APIStatusError as e:
        log.error("Claude API error %s: %s", e.status_code, e.message)
        msg = str(e.message).lower()
        if "credit" in msg or "billing" in msg or e.status_code in (401, 403):
            await alert_admin(bot, f"⚠️ Claude API ishlamayapti: {e.message}\nBalansni tekshiring: platform.claude.com")
            return await message.answer(t["unavailable"])
        return await message.answer(t["error"])
    except Exception:
        log.exception("Claude call failed")
        return await message.answer(t["error"])

    add_usage(uid)
    write_log(uid, "question", message.text, answer, in_tok, out_tok, MODEL)
    await send_long(message, answer or t["error"], reply_markup=menu_kb(lang))


@router.message()
async def other_content(message: Message):
    await message.answer(T[get_lang(message.from_user.id)]["text_only"])


async def main():
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    log.info("Bot ishga tushdi. Model: %s", MODEL)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

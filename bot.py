"""Shifokor yordamchi boti: ovulyatsiya kalkulyatori + Claude orqali savollarga javob."""

import asyncio
import contextvars
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
from aiogram.exceptions import TelegramBadRequest
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
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE IF NOT EXISTS admins(user_id INTEGER PRIMARY KEY);
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
# Premium (custom) emoji ID'lari Railway Variables orqali beriladi: EMOJI_CALC, EMOJI_OTHER, ...
# ID'ni bilish uchun botga "/emoji 😀" deb premium emoji bilan yozing.
# Ishlashi uchun bot egasida Telegram Premium bo'lishi kerak.
ICON_KEYS = ["calc", "other", "lang", "yes", "no", "uz", "ru"]
ICON_NAMES = {
    "calc": "🗓 Ovulyatsiyani hisoblash",
    "other": "❓ Boshqa savol",
    "lang": "🌐 Tilni o'zgartirish",
    "yes": "✅ Ha, doim bir xil",
    "no": "❌ Yo'q, o'zgarib turadi",
    "uz": "🇺🇿 O'zbekcha",
    "ru": "🇷🇺 Русский",
}
ICONS = {k: os.getenv(f"EMOJI_{k.upper()}", "").strip() or None for k in ICON_KEYS}
for _k, _v in db.execute("SELECT key, value FROM settings WHERE key LIKE 'emoji_%'").fetchall():
    if _k[6:] in ICONS:
        ICONS[_k[6:]] = _v or None


def save_icon(key: str, emoji_id: str | None) -> None:
    ICONS[key] = emoji_id
    db.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)", (f"emoji_{key}", emoji_id or ""))
    db.commit()


def admin_ids() -> set[int]:
    ids = {r[0] for r in db.execute("SELECT user_id FROM admins").fetchall()}
    if ADMIN_ID:
        ids.add(ADMIN_ID)
    return ids


def is_admin(uid: int) -> bool:
    return uid in admin_ids()
USE_STYLES = os.getenv("BUTTON_STYLES", "1") != "0"  # rangli tugmalar


def strip_emoji(s: str) -> str:
    """'🗓 Ovulyatsiyani hisoblash' -> 'Ovulyatsiyani hisoblash'"""
    first, _, rest = s.partition(" ")
    return rest if rest and not any(ch.isalnum() for ch in first) else s


def label(text: str, icon_key: str) -> str:
    return strip_emoji(text) if ICONS.get(icon_key) else text


def style(name: str | None) -> str | None:
    return name if USE_STYLES else None


def ibtn(text: str, data: str, icon_key: str | None = None, st: str | None = None) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=label(text, icon_key) if icon_key else text,
        callback_data=data,
        icon_custom_emoji_id=ICONS.get(icon_key) if icon_key else None,
        style=style(st),
    )


def kbtn(text: str, icon_key: str, st: str | None = None) -> KeyboardButton:
    return KeyboardButton(text=label(text, icon_key), icon_custom_emoji_id=ICONS.get(icon_key), style=style(st))


def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            ibtn("🇺🇿 O'zbekcha", "lang:uz", "uz", "primary"),
            ibtn("🇷🇺 Русский", "lang:ru", "ru", "primary"),
        ]]
    )


def menu_kb(lang: str) -> ReplyKeyboardMarkup:
    t = T[lang]
    return ReplyKeyboardMarkup(
        keyboard=[
            [kbtn(t["btn_calc"], "calc", "primary")],
            [kbtn(t["btn_other"], "other", "success")],
            [kbtn(t["btn_lang"], "lang")],
        ],
        resize_keyboard=True,
    )


def cycle_kb() -> InlineKeyboardMarkup:
    nums = list(range(21, 36))
    rows = [
        [ibtn(str(n), f"cyc:{n}", st="primary" if n == 28 else None) for n in nums[i:i + 5]]
        for i in range(0, len(nums), 5)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def regular_kb(lang: str) -> InlineKeyboardMarkup:
    t = T[lang]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [ibtn(t["yes"], "reg:yes", "yes", "success")],
            [ibtn(t["no"], "reg:no", "no", "danger")],
        ]
    )


def _variants(key: str) -> set[str]:
    return {T[l][key] for l in T} | {strip_emoji(T[l][key]) for l in T}


CALC_BTNS = _variants("btn_calc")
OTHER_BTNS = _variants("btn_other")
LANG_BTNS = _variants("btn_lang")


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
    if not admin_ids() or time.time() - _last_admin_alert < 3600:
        return
    _last_admin_alert = time.time()
    for aid in admin_ids():
        try:
            await bot.send_message(aid, text)
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
admin_router = Router()


# ---------- Premium emoji: xato bo'lsa emojisiz qayta yuborish ----------
_strict_icons: contextvars.ContextVar[bool] = contextvars.ContextVar("strict_icons", default=False)


def _strip_markup(rm):
    if isinstance(rm, InlineKeyboardMarkup):
        return InlineKeyboardMarkup(inline_keyboard=[
            [b.model_copy(update={"icon_custom_emoji_id": None}) for b in row] for row in rm.inline_keyboard
        ])
    if isinstance(rm, ReplyKeyboardMarkup):
        return rm.model_copy(update={"keyboard": [
            [b.model_copy(update={"icon_custom_emoji_id": None}) for b in row] for row in rm.keyboard
        ]})
    return rm


def _has_icons(rm) -> bool:
    rows = getattr(rm, "inline_keyboard", None) or getattr(rm, "keyboard", None) or []
    return any(getattr(b, "icon_custom_emoji_id", None) for row in rows for b in row)


async def emoji_fallback(make_request, bot, method):
    try:
        return await make_request(bot, method)
    except TelegramBadRequest as e:
        rm = getattr(method, "reply_markup", None)
        if _strict_icons.get() or rm is None or not _has_icons(rm):
            raise
        log.warning("Premium emoji rad etildi, emojisiz yuborilmoqda: %s", e.message)
        return await make_request(bot, method.model_copy(update={"reply_markup": _strip_markup(rm)}))


# ---------- /addpremium (faqat admin) ----------
class PE(StatesGroup):
    wait = State()


def pe_list_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(
            text=f"{ICON_NAMES[k]}  {'✅' if ICONS.get(k) else '➖'}",
            callback_data=f"pe:{k}",
            icon_custom_emoji_id=ICONS.get(k),
        )]
        for k in ICON_KEYS
    ]
    rows.append([InlineKeyboardButton(text="🗑 Hammasini o'chirish", callback_data="pe:__clear")])
    rows.append([InlineKeyboardButton(text="✖️ Yopish", callback_data="pe:__close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


PE_LIST_TEXT = (
    "✨ Premium emoji sozlamalari\n\n"
    "Qaysi tugmaga premium emoji qo'yamiz? ✅ — qo'yilgan, ➖ — qo'yilmagan.\n"
    "Biror tugmada chiqmasa, uni qayta tanlab boshqa emoji yuboring."
)


@admin_router.message(Command("addpremium"))
async def cmd_addpremium(message: Message, state: FSMContext):
    uid = message.from_user.id
    if not admin_ids():
        db.execute("INSERT OR IGNORE INTO admins(user_id) VALUES(?)", (uid,))
        db.commit()
        await message.answer("👑 Siz bot admini bo'ldingiz (birinchi bo'lib /addpremium yozgan odam).")
    if not is_admin(uid):
        return
    await state.clear()
    await message.answer(PE_LIST_TEXT, reply_markup=pe_list_kb())


@admin_router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    lang = get_lang(message.from_user.id)
    await message.answer("Bekor qilindi.", reply_markup=menu_kb(lang))


@admin_router.callback_query(F.data.startswith("pe:"))
async def cb_pe(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id):
        return await cb.answer()
    key = cb.data[3:]
    await cb.answer()
    if key == "__close":
        await state.clear()
        return await cb.message.delete()
    if key == "__clear":
        for k in ICON_KEYS:
            save_icon(k, None)
        await state.clear()
        return await cb.message.edit_text("🗑 Barcha premium emojilar o'chirildi.\n\n" + PE_LIST_TEXT, reply_markup=pe_list_kb())
    if key.startswith("__del_"):
        k = key[6:]
        save_icon(k, None)
        await state.clear()
        return await cb.message.edit_text(f"🗑 «{ICON_NAMES[k]}» dan emoji olib tashlandi.\n\n" + PE_LIST_TEXT, reply_markup=pe_list_kb())
    if key not in ICON_KEYS:
        return
    await state.set_state(PE.wait)
    await state.update_data(pe_key=key)
    extra = []
    if ICONS.get(key):
        extra = [[InlineKeyboardButton(text="🗑 Shu tugmadan olib tashlash", callback_data=f"pe:__del_{key}")]]
    await cb.message.answer(
        f"«{ICON_NAMES[key]}» tugmasi uchun 1 ta premium (animatsiyali) emoji yuboring.\n\nBekor qilish: /cancel",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=extra) if extra else None,
    )


@admin_router.message(PE.wait)
async def pe_got(message: Message, state: FSMContext):
    ents = [e for e in (message.entities or []) + (message.caption_entities or []) if e.type == "custom_emoji"]
    sticker_emoji = None
    if message.sticker and message.sticker.custom_emoji_id:
        sticker_emoji = message.sticker.custom_emoji_id
    emoji_id = ents[0].custom_emoji_id if ents else sticker_emoji
    if not emoji_id:
        return await message.answer(
            "Bu oddiy emoji 🙂 Premium (animatsiyali) emoji yuboring.\n"
            "Emoji panelida oddiy emojilardan pastda, ⭐ belgili to'plamlarda bo'ladi.\n\nBekor qilish: /cancel"
        )
    key = (await state.get_data()).get("pe_key")
    # Telegram qabul qiladimi — namunani yuborib tekshiramiz
    token = _strict_icons.set(True)
    try:
        preview = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
            text=strip_emoji(ICON_NAMES[key]), callback_data="pe:__noop", icon_custom_emoji_id=emoji_id)]])
        await message.answer("Ko'rinishi 👇", reply_markup=preview)
    except TelegramBadRequest as e:
        return await message.answer(
            f"❌ Telegram bu emojini tugmaga qo'yishga ruxsat bermadi.\n({e.message})\n\n"
            "Bot egasida (BotFather'da botni ochgan akkauntda) Telegram Premium bo'lishi kerak. "
            "Boshqa emoji yuborib ko'ring yoki /cancel"
        )
    finally:
        _strict_icons.reset(token)
    save_icon(key, emoji_id)
    await state.clear()
    lang = get_lang(message.from_user.id)
    await message.answer(
        f"✅ «{ICON_NAMES[key]}» tugmasiga saqlandi. Menyu yangilandi 👇",
        reply_markup=menu_kb(lang),
    )
    await message.answer(PE_LIST_TEXT, reply_markup=pe_list_kb())


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    save_user(message)
    await message.answer(CHOOSE_LANG, reply_markup=lang_kb())


@router.message(Command("emoji"))
async def cmd_emoji(message: Message):
    """Premium emoji ID'larini ko'rsatadi: /emoji 😀🔥"""
    found = [
        (e.extract_from(message.text or ""), e.custom_emoji_id)
        for e in (message.entities or [])
        if e.type == "custom_emoji"
    ]
    if not found:
        return await message.answer("Premium emoji bilan yozing, masalan: /emoji 😀")
    lines = [f"{ch}  →  {eid}" for ch, eid in found]
    await message.answer("Premium emoji ID'lari:\n\n" + "\n".join(lines))


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
    if not is_admin(message.from_user.id):
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
    if used_today(uid) >= DAILY_LIMIT and not is_admin(uid):
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
    bot.session.middleware(emoji_fallback)
    dp.include_router(admin_router)
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    log.info("Bot ishga tushdi. Model: %s", MODEL)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

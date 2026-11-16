"""Shifokor yordamchi boti: ovulyatsiya kalkulyatori + Claude orqali savollarga javob."""

import asyncio
import base64
import contextvars
import html
import io
import json
import logging
import os
import re
import sqlite3
import time
from collections import defaultdict, deque
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from PIL import Image

import anthropic
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatAction
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    LinkPreviewOptions,
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
    CREATE TABLE IF NOT EXISTS payments(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER,
        status TEXT, created_at TEXT);
    """
)
# users jadvaliga yangi ustunlar (eski bazada bo'lmasa qo'shiladi)
_cols = {r[1] for r in db.execute("PRAGMA table_info(users)").fetchall()}
for _col, _type in [("sub", "TEXT DEFAULT ''"), ("ig", "TEXT"), ("credits", "INTEGER DEFAULT 0"),
                    ("banned", "INTEGER DEFAULT 0")]:
    if _col not in _cols:
        db.execute(f"ALTER TABLE users ADD COLUMN {_col} {_type}")
db.commit()

DEFAULT_SETTINGS = {
    "insta_url": os.getenv("INSTA_URL", ""),
    "card": os.getenv("CARD_NUMBER", ""),
    "holder": os.getenv("CARD_HOLDER", ""),
    "price_full": os.getenv("PRICE_FULL", "10000"),
    "price_sub": os.getenv("PRICE_SUB", "5000"),
}


def get_setting(key: str) -> str:
    row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row and row[0] is not None else DEFAULT_SETTINGS.get(key, "")


def set_setting(key: str, value: str) -> None:
    db.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)", (key, value))
    db.commit()


def user_field(uid: int, field: str, default=None):
    row = db.execute(f"SELECT {field} FROM users WHERE user_id=?", (uid,)).fetchone()
    return row[0] if row and row[0] is not None else default


def set_user_field(uid: int, field: str, value) -> None:
    db.execute("INSERT OR IGNORE INTO users(user_id, created_at) VALUES(?, ?)", (uid, now().isoformat()))
    db.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, uid))
    db.commit()


def is_subscribed(uid: int) -> bool:
    return user_field(uid, "sub", "") == "ok"


def money(n: int | str) -> str:
    return f"{int(n):,}".replace(",", " ")


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
    ids |= {int(x) for x in re.findall(r"\d+", os.getenv("ADMIN_IDS", ""))}
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
    if not is_admin(message.from_user.id):
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


# ======================================================================
#  Instagram obuna + pullik savollar
# ======================================================================
paid_router = Router()
ADMIN_CODE = os.getenv("ADMIN_CODE", "").strip()


class SubIG(StatesGroup):
    wait = State()


class Pay(StatesGroup):
    receipt = State()


ALL_MENU = CALC_BTNS | OTHER_BTNS | LANG_BTNS
not_menu = ~F.text.in_(ALL_MENU) & ~F.text.startswith("/")


async def clear_user_state(bot: Bot, uid: int) -> None:
    try:
        await DP.fsm.get_context(bot=bot, chat_id=uid, user_id=uid).clear()
    except Exception:
        log.exception("state clear failed")


async def send_admins(bot: Bot, text: str, kb=None, photo: str | None = None, document: str | None = None) -> None:
    ids = admin_ids()
    if not ids:
        log.warning("Admin yo'q! Xabar yuborilmadi: %s", text[:80])
    for aid in ids:
        try:
            if photo:
                await bot.send_photo(aid, photo, caption=text, reply_markup=kb, parse_mode="HTML")
            elif document:
                await bot.send_document(aid, document, caption=text, reply_markup=kb, parse_mode="HTML")
            else:
                await bot.send_message(aid, text, reply_markup=kb, parse_mode="HTML",
                                       link_preview_options=LinkPreviewOptions(is_disabled=True))
        except Exception:
            log.exception("send to admin %s failed", aid)


def insta_url() -> str:
    return get_setting("insta_url").strip()


def insta_kb(lang: str) -> InlineKeyboardMarkup:
    t = T[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["btn_insta"], url=insta_url(), style=style("primary"))],
        [ibtn(t["btn_subbed"], "sub:req", st="success")],
    ])


async def ensure_sub(message: Message, lang: str, uid: int) -> bool:
    """Obuna bo'lmagan bo'lsa, obuna bo'lishni so'raydi va False qaytaradi."""
    if not insta_url() or is_admin(uid) or is_subscribed(uid):
        return True
    if user_field(uid, "sub", "") == "pending":
        await message.answer(T[lang]["sub_pending"])
        return False
    await message.answer(T[lang]["sub_need"], reply_markup=insta_kb(lang))
    return False


def user_label(u) -> str:
    uname = f" (@{u.username})" if u.username else ""
    return f"{html.escape(u.full_name)}{uname}\n🆔 <code>{u.id}</code>"


@paid_router.callback_query(F.data == "sub:start")
async def cb_sub_start(cb: CallbackQuery):
    await cb.answer()
    lang = get_lang(cb.from_user.id)
    await ensure_sub(cb.message, lang, cb.from_user.id)


@paid_router.callback_query(F.data == "sub:req")
async def cb_sub_req(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    uid = cb.from_user.id
    lang = get_lang(uid)
    st = user_field(uid, "sub", "")
    if st == "ok":
        return await cb.message.answer(T[lang]["sub_ok"], reply_markup=menu_kb(lang))
    if st == "pending":
        return await cb.message.answer(T[lang]["sub_pending"])
    await state.set_state(SubIG.wait)
    await cb.message.answer(T[lang]["ask_ig"])


IG_RE = re.compile(r"(?:instagram\.com/)?@?([A-Za-z0-9._]{1,30})")


@paid_router.message(SubIG.wait, F.text, not_menu)
async def got_ig(message: Message, state: FSMContext, bot: Bot):
    uid = message.from_user.id
    lang = get_lang(uid)
    m = IG_RE.search(message.text.strip())
    if not m:
        return await message.answer(T[lang]["bad_ig"])
    ig = m.group(1).strip(".")
    set_user_field(uid, "ig", ig)
    await state.clear()
    followers = insta_url().rstrip("/") + "/followers/"
    if get_setting("sub_mode") == "manual":
        set_user_field(uid, "sub", "pending")
        await message.answer(T[lang]["sub_sent"], reply_markup=menu_kb(lang))
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Obuna bo'lgan", callback_data=f"adm:sub:ok:{uid}", style=style("success")),
            InlineKeyboardButton(text="❌ Obuna bo'lmagan", callback_data=f"adm:sub:no:{uid}", style=style("danger")),
        ]])
        head, tail = "📸 <b>Yangi obuna so'rovi</b>", "Tasdiqlasangiz, mijozga hisoblash ochiladi."
    else:
        # Avto rejim: darhol ochamiz, adminlar keyin tekshirib bekor qilishi mumkin
        set_user_field(uid, "sub", "ok")
        await message.answer(T[lang]["sub_ok"], reply_markup=menu_kb(lang))
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="❌ Obuna yo'q — bekor qilish", callback_data=f"adm:sub:no:{uid}",
                                 style=style("danger")),
        ]])
        head, tail = "📸 <b>Yangi obunachi</b> (avtomatik ochildi)", "Obuna bo'lmagan bo'lsa — ❌ ni bosing."
    await send_admins(
        bot,
        f"{head}\n\n"
        f"👤 {user_label(message.from_user)}\n"
        f"📷 Instagram: https://instagram.com/{html.escape(ig)}\n\n"
        f"Tekshirish: {followers} → qidiruvga <code>{html.escape(ig)}</code> yozing.\n{tail}",
        kb,
    )


async def show_payment(message: Message, state: FSMContext, lang: str, uid: int) -> None:
    t = T[lang]
    card = get_setting("card").strip()
    if not card:
        await message.answer(t["pay_not_ready"])
        return
    pending = db.execute("SELECT 1 FROM payments WHERE user_id=? AND status='pending'", (uid,)).fetchone()
    if pending:
        await message.answer(t["pay_pending"])
        return
    sub = is_subscribed(uid)
    price = get_setting("price_sub") if sub else get_setting("price_full")
    text = t["pay_info"].format(
        price=money(price),
        discount=t["pay_discount"] if sub else "",
        card=f"<code>{html.escape(card)}</code>",
        holder=html.escape(get_setting("holder") or "—"),
    )
    kb = None
    if not sub and insta_url():
        text += "\n\n" + t["pay_sub_hint"].format(sub_price=money(get_setting("price_sub")))
        kb = InlineKeyboardMarkup(inline_keyboard=[[ibtn(t["btn_get_discount"], "sub:start", st="success")]])
    await state.set_state(Pay.receipt)
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


async def handle_receipt(message: Message, bot: Bot, state: FSMContext) -> None:
    uid = message.from_user.id
    lang = get_lang(uid)
    t = T[lang]
    await state.clear()
    if user_field(uid, "banned", 0):
        await message.answer(t["pay_no"])
        return
    if db.execute("SELECT 1 FROM payments WHERE user_id=? AND status='pending'", (uid,)).fetchone():
        await message.answer(t["pay_pending"])
        return
    sub = is_subscribed(uid)
    amount = int(get_setting("price_sub") if sub else get_setting("price_full"))
    cur = db.execute(
        "INSERT INTO payments(user_id, amount, status, created_at) VALUES(?,?,?,?)",
        (uid, amount, "pending", now().isoformat()),
    )
    db.commit()
    pid = cur.lastrowid
    await message.answer(t["pay_sent"], reply_markup=menu_kb(lang))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Pul keldi", callback_data=f"adm:pay:ok:{pid}", style=style("success")),
         InlineKeyboardButton(text="❌ Kelmadi", callback_data=f"adm:pay:no:{pid}", style=style("danger"))],
        [InlineKeyboardButton(text="🚫 Bloklash (yolg'on chek)", callback_data=f"adm:ban:{pid}")],
    ])
    caption = (
        f"💰 <b>To'lov cheki #{pid}</b>\n\n"
        f"👤 {user_label(message.from_user)}\n"
        f"💵 Summa: <b>{money(amount)} so'm</b> ({'obunachi, 50%' if sub else 'oddiy narx'})\n\n"
        "Kartangizga pul tushganini tekshiring."
    )
    if message.photo:
        fid, uniq, mime = message.photo[-1].file_id, message.photo[-1].file_unique_id, "image/jpeg"
    else:
        fid, uniq, mime = message.document.file_id, message.document.file_unique_id, message.document.mime_type or ""
    smart = auto_cheque_on() and (mime.startswith("image/") or mime == "application/pdf")
    if smart:
        caption += "\n\n🤖 <b>Chek avtomatik tekshirilmoqda…</b> To'g'ri bo'lsa, o'zi tasdiqlanadi va sizga xabar keladi."
    if message.photo:
        await send_admins(bot, caption, kb, photo=fid)
    else:
        await send_admins(bot, caption, kb, document=fid)
    if smart:
        asyncio.create_task(check_cheque(bot, pid, fid, uniq, mime))


@paid_router.message(Pay.receipt, F.photo | F.document)
async def got_receipt(message: Message, bot: Bot, state: FSMContext):
    await handle_receipt(message, bot, state)


@paid_router.message(Pay.receipt, F.text, not_menu)
async def receipt_text(message: Message):
    await message.answer(T[get_lang(message.from_user.id)]["pay_need_photo"])


# ---------- 🧾 Aqlli chek tekshiruvi (Claude chekni o'qiydi) ----------
CHEQUE_SYSTEM = (
    "Sen to'lov cheklarini (Click, Payme, Uzum, Paynet, bank ilovalari skrinshotlari) o'qiydigan yordamchisan. "
    "Faqat JSON qaytar. Ko'rmagan narsangni o'ylab topma — bilmasang null yoz."
)
CHEQUE_PROMPT = """Bu rasm to'lov chekimi? Undan ma'lumotlarni ol. Faqat shu JSON:
{"is_receipt": true/false,
 "success": true/false/null,
 "amount": 5000,
 "recipient_card_last4": "9012",
 "recipient_name": "...",
 "datetime": "2026-11-16 14:30",
 "edited_signs": false}
success — to'lov muvaffaqiyatli o'tganmi (Успешно, Muvaffaqiyatli, Выполнено, ✓).
amount — o'tkazilgan asosiy summa so'mda, butun son (komissiyasiz); bo'lmasa null.
recipient_card_last4 — QABUL QILUVCHI karta raqamining oxirgi 4 raqami; bo'lmasa null.
datetime — chekdagi sana va vaqt (YYYY-MM-DD HH:MM); bo'lmasa null.
edited_signs — tahrirlangan/soxta belgilar ko'rinsa true (shriftlar mos emas, raqamlar ustidan yozilgan)."""


def _digits(x) -> str:
    return re.sub(r"\D", "", str(x or ""))


async def read_cheque(data: bytes, mime: str) -> dict:
    if mime == "application/pdf":
        block = {"type": "document", "source": {"type": "base64", "media_type": mime,
                                                 "data": base64.b64encode(data).decode()}}
    else:
        im = Image.open(io.BytesIO(data)).convert("RGB")
        im.thumbnail((1600, 1600))
        out = io.BytesIO()
        im.save(out, "JPEG", quality=90)
        block = {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                              "data": base64.b64encode(out.getvalue()).decode()}}
    resp = await client.messages.create(
        model=MODEL, max_tokens=600, system=CHEQUE_SYSTEM,
        messages=[{"role": "user", "content": [block, {"type": "text", "text": CHEQUE_PROMPT}]}],
    )
    raw = "".join(b.text for b in resp.content if b.type == "text")
    write_log(0, "cheque", "", raw[:500], resp.usage.input_tokens or 0, resp.usage.output_tokens or 0, MODEL)
    m = re.search(r"\{.*\}", raw, re.S)
    return json.loads(m.group(0)) if m else {}


async def approve_payment(bot: Bot, pid: int, note: str | None = None) -> bool:
    """To'lovni tasdiqlaydi: mijozga 1 ta savol ochiladi. Allaqachon ko'rilgan bo'lsa False."""
    row = db.execute("SELECT user_id, status FROM payments WHERE id=?", (pid,)).fetchone()
    if not row or row[1] != "pending":
        return False
    uid = row[0]
    db.execute("UPDATE payments SET status='ok' WHERE id=?", (pid,))
    db.execute("UPDATE users SET credits = COALESCE(credits, 0) + 1 WHERE user_id=?", (uid,))
    db.commit()
    lang = get_lang(uid)
    await clear_user_state(bot, uid)
    await bot.send_message(uid, T[lang]["pay_ok"], reply_markup=menu_kb(lang))
    if note:
        await send_admins(bot, note)
    return True


async def check_cheque(bot: Bot, pid: int, file_id: str, unique_id: str, mime: str) -> None:
    """Chekni Claude bilan o'qib tekshiradi: summa, karta, sana, takror chek. Hammasi mos — avtomatik tasdiq."""
    reasons, info = [], {}
    row = db.execute("SELECT amount, created_at FROM payments WHERE id=?", (pid,)).fetchone()
    need, created = int(row[0]), datetime.fromisoformat(row[1])
    try:
        used = get_setting(f"cheque_{unique_id}")
        if used:
            reasons.append(f"bu chek avval ishlatilgan (#{used})")
        buf = io.BytesIO()
        await bot.download(file_id, destination=buf)
        info = await asyncio.wait_for(read_cheque(buf.getvalue(), mime), timeout=90)
        amount = int(_digits(info.get("amount")) or 0)
        last4 = _digits(info.get("recipient_card_last4"))[-4:]
        mine = _digits(get_setting("card"))[-4:]
        if not info.get("is_receipt"):
            reasons.append("rasm to'lov chekiga o'xshamaydi")
        if info.get("success") is False:
            reasons.append("chekda to'lov muvaffaqiyatli emas")
        if info.get("edited_signs"):
            reasons.append("tahrirlangan belgilar bor")
        if amount < need - 500:
            reasons.append(f"summa mos emas ({money(amount) if amount else 'o‘qilmadi'} / kerak {money(need)})")
        if not last4 or last4 != mine:
            reasons.append(f"qabul qiluvchi karta mos emas (*{last4 or '?'} / sizniki *{mine})")
        dt = None
        try:
            dt = datetime.strptime(str(info.get("datetime"))[:16], "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
        except (TypeError, ValueError):
            pass
        if not dt:
            reasons.append("chekda sana o'qilmadi")
        elif not (now() - timedelta(hours=36) <= dt <= now() + timedelta(minutes=30)):
            reasons.append("chek sanasi eski yoki noto'g'ri")
        elif dt < created - timedelta(hours=3):
            reasons.append(f"chek so'rovdan ancha oldin qilingan ({info.get('datetime')}) — eski chek bo'lishi mumkin")
    except Exception as e:
        log.exception("cheque check failed")
        reasons.append(f"chek o'qilmadi ({str(e)[:120]})")

    status = db.execute("SELECT status FROM payments WHERE id=?", (pid,)).fetchone()[0]
    if status != "pending":  # admin allaqachon qaror qilgan
        return
    if reasons:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Pul keldi", callback_data=f"adm:pay:ok:{pid}", style=style("success")),
             InlineKeyboardButton(text="❌ Kelmadi", callback_data=f"adm:pay:no:{pid}", style=style("danger"))],
            [InlineKeyboardButton(text="🚫 Bloklash (yolg'on chek)", callback_data=f"adm:ban:{pid}")],
        ])
        await send_admins(
            bot,
            f"🧾 #{pid} — <b>chek avtomatik tasdiqlanmadi</b>:\n• "
            + "\n• ".join(html.escape(r, quote=False) for r in reasons)
            + "\n\nKartangizni tekshirib, o'zingiz qaror qiling 👇",
            kb,
        )
        return
    set_setting(f"cheque_{unique_id}", str(pid))
    await approve_payment(
        bot, pid,
        f"✅ #{pid} — <b>chek avtomatik tasdiqlandi</b>: {money(int(_digits(info.get('amount'))))} so'm → karta "
        f"*{_digits(get_setting('card'))[-4:]}, {html.escape(str(info.get('datetime')))}.\n"
        "Vaqtingiz bo'lganda kartangizga tushganini tekshirib qo'ying.",
    )


def auto_cheque_on() -> bool:
    return client is not None and get_setting("auto_cheque") != "off"


# ---------- Admin: tasdiqlash tugmalari ----------
async def _mark_done(cb: CallbackQuery, note: str) -> None:
    try:
        if cb.message.photo or cb.message.document:
            await cb.message.edit_caption(caption=(cb.message.html_text or "") + f"\n\n{note}",
                                          parse_mode="HTML", reply_markup=None)
        else:
            await cb.message.edit_text((cb.message.html_text or "") + f"\n\n{note}", parse_mode="HTML",
                                       reply_markup=None,
                                       link_preview_options=LinkPreviewOptions(is_disabled=True))
    except Exception:
        log.exception("edit admin msg failed")


@admin_router.callback_query(F.data.startswith("adm:"))
async def cb_admin(cb: CallbackQuery, bot: Bot):
    if not is_admin(cb.from_user.id):
        return await cb.answer()
    parts = cb.data.split(":")
    who = cb.from_user.first_name

    if parts[1] == "sub":
        action, uid = parts[2], int(parts[3])
        cur = user_field(uid, "sub", "")
        if (action == "ok" and cur != "pending") or (action == "no" and cur not in ("pending", "ok")):
            await cb.answer("Bu so'rov allaqachon ko'rib chiqilgan", show_alert=True)
            return await _mark_done(cb, "ℹ️ Allaqachon ko'rib chiqilgan")
        lang = get_lang(uid)
        if action == "ok":
            set_user_field(uid, "sub", "ok")
            await cb.answer("✅ Tasdiqlandi")
            await _mark_done(cb, f"✅ Obuna tasdiqlandi ({html.escape(who)})")
            await clear_user_state(bot, uid)
            await bot.send_message(uid, T[lang]["sub_ok"], reply_markup=menu_kb(lang))
        else:
            set_user_field(uid, "sub", "")
            await cb.answer("❌ Rad etildi")
            await _mark_done(cb, f"❌ Obuna topilmadi ({html.escape(who)})")
            if insta_url():
                await bot.send_message(uid, T[lang]["sub_no"], reply_markup=insta_kb(lang))
            else:
                await bot.send_message(uid, T[lang]["sub_no"])
        return

    if parts[1] in ("pay", "ban"):
        pid = int(parts[-1])
        row = db.execute("SELECT user_id, amount, status FROM payments WHERE id=?", (pid,)).fetchone()
        if not row:
            return await cb.answer("Topilmadi", show_alert=True)
        uid, amount, status = row
        if status != "pending":
            await cb.answer("Bu chek allaqachon ko'rib chiqilgan", show_alert=True)
            return await _mark_done(cb, "ℹ️ Allaqachon ko'rib chiqilgan")
        lang = get_lang(uid)
        if parts[1] == "pay" and parts[2] == "ok":
            await cb.answer("✅ Tasdiqlandi")
            await _mark_done(cb, f"✅ To'lov tasdiqlandi ({html.escape(who)})")
            await approve_payment(bot, pid)
        elif parts[1] == "pay":
            db.execute("UPDATE payments SET status='no' WHERE id=?", (pid,))
            db.commit()
            await cb.answer("❌ Rad etildi")
            await _mark_done(cb, f"❌ To'lov topilmadi ({html.escape(who)})")
            await bot.send_message(uid, T[lang]["pay_no"])
        else:  # ban
            db.execute("UPDATE payments SET status='ban' WHERE id=?", (pid,))
            db.commit()
            set_user_field(uid, "banned", 1)
            await cb.answer("🚫 Bloklandi")
            await _mark_done(cb, f"🚫 Foydalanuvchi bloklandi ({html.escape(who)})")
            await bot.send_message(uid, T[lang]["pay_no"])


# ---------- Admin buyruqlari ----------
ADMIN_HELP = (
    "👑 <b>Admin buyruqlari</b>\n\n"
    "/settings — joriy sozlamalar\n"
    "/setinsta <code>https://instagram.com/username</code> — Instagram sahifa\n"
    "/setcard <code>8600123412341234 Ism Familiya</code> — to'lov kartasi\n"
    "/setprice <code>10000 5000</code> — narx: oddiy va obunachi\n"
    "/addcredit <code>ID 1</code> — foydalanuvchiga bepul savol berish\n"
    "/autochek <code>on</code> | <code>off</code> — chekni avtomatik (aqlli) tekshirish\n"
    "/obuna <code>auto</code> | <code>manual</code> — Instagram obunani darhol ochish yoki qo'lda tasdiqlash\n"
    "/stats — statistika\n"
    "/addpremium — tugmalarga premium emoji\n\n"
    "Obuna so'rovlari va to'lov cheklari shu yerga ✅/❌ tugmalari bilan keladi."
)


@admin_router.message(Command("admin"))
async def cmd_admin(message: Message, command: CommandObject):
    uid = message.from_user.id
    if is_admin(uid):
        return await message.answer(ADMIN_HELP, parse_mode="HTML")
    if ADMIN_CODE and (command.args or "").strip() == ADMIN_CODE:
        db.execute("INSERT OR IGNORE INTO admins(user_id) VALUES(?)", (uid,))
        db.commit()
        return await message.answer("👑 Siz admin bo'ldingiz!\n\n" + ADMIN_HELP, parse_mode="HTML")
    # noto'g'ri kod — hech narsa demaymiz


@admin_router.message(Command("settings"))
async def cmd_settings(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "⚙️ <b>Sozlamalar</b>\n\n"
        f"📷 Instagram: {html.escape(insta_url() or '— (obuna tekshiruvi o‘chiq)')}\n"
        f"💳 Karta: <code>{html.escape(get_setting('card') or '—')}</code>\n"
        f"👤 Egasi: {html.escape(get_setting('holder') or '—')}\n"
        f"💵 Narx: {money(get_setting('price_full'))} so'm, obunachiga {money(get_setting('price_sub'))} so'm\n"
        f"🤖 Aqlli chek tekshiruvi: {'yoqilgan' if auto_cheque_on() else 'o‘chirilgan' + ('' if client else ' (Claude kaliti yo‘q)')}\n"
        f"👑 Adminlar soni: {len(admin_ids())}\n\n" + ADMIN_HELP,
        parse_mode="HTML",
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@admin_router.message(Command("obuna"))
async def cmd_obuna(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return
    arg = (command.args or "").strip().lower()
    if arg in ("auto", "manual"):
        set_setting("sub_mode", arg)
    mode = get_setting("sub_mode") or "auto"
    await message.answer(
        f"📸 Obuna tekshiruvi: <b>{'avto' if mode != 'manual' else 'qo‘lda'}</b>\n\n"
        "/obuna auto — mijoz username yozishi bilan hisoblash ochiladi, sizga ❌ bekor qilish tugmasi keladi\n"
        "/obuna manual — siz ✅ bosmaguningizcha ochilmaydi",
        parse_mode="HTML",
    )


@admin_router.message(Command("autochek", "autocheck"))
async def cmd_autochek(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return
    arg = (command.args or "").strip().lower()
    if arg in ("on", "off"):
        set_setting("auto_cheque", arg)
    state_txt = "yoqilgan ✅" if auto_cheque_on() else "o'chirilgan ❌"
    extra = "" if client else "\n⚠️ Claude API kaliti qo'yilmagan — kalit qo'yilgach ishlaydi."
    await message.answer(f"🤖 Aqlli chek tekshiruvi: {state_txt}{extra}\n\nYoqish: /autochek on\nO'chirish: /autochek off")


@admin_router.message(Command("setinsta"))
async def cmd_setinsta(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return
    arg = (command.args or "").strip()
    if arg.lower() in ("off", "o'chir", "-"):
        set_setting("insta_url", "")
        return await message.answer("📷 Instagram tekshiruvi o'chirildi: hisoblash hammaga ochiq.")
    m = IG_RE.search(arg) if arg else None
    if not m:
        return await message.answer("Masalan: /setinsta https://instagram.com/username")
    url = f"https://instagram.com/{m.group(1)}"
    set_setting("insta_url", url)
    await message.answer(f"✅ Instagram saqlandi: {url}", link_preview_options=LinkPreviewOptions(is_disabled=True))


@admin_router.message(Command("setcard"))
async def cmd_setcard(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return
    arg = (command.args or "").strip()
    m = re.match(r"([\d\s]{12,25})\s*(.*)", arg)
    digits = re.sub(r"\D", "", m.group(1)) if m else ""
    if not (m and 12 <= len(digits) <= 19):
        return await message.answer("Masalan: /setcard 8600123412341234 Ism Familiya")
    card = " ".join(digits[i:i + 4] for i in range(0, len(digits), 4))
    set_setting("card", card)
    if m.group(2).strip():
        set_setting("holder", m.group(2).strip())
    await message.answer(f"✅ Karta saqlandi: <code>{card}</code>\n👤 {html.escape(get_setting('holder') or '—')}",
                         parse_mode="HTML")


@admin_router.message(Command("setprice"))
async def cmd_setprice(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return
    nums = re.findall(r"\d+", (command.args or "").replace(" 000", "000"))
    if len(nums) != 2:
        return await message.answer("Masalan: /setprice 10000 5000")
    set_setting("price_full", nums[0])
    set_setting("price_sub", nums[1])
    await message.answer(f"✅ Narx: {money(nums[0])} so'm, obunachiga {money(nums[1])} so'm")


@admin_router.message(Command("addcredit"))
async def cmd_addcredit(message: Message, command: CommandObject, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    nums = re.findall(r"\d+", command.args or "")
    if not nums:
        return await message.answer("Masalan: /addcredit 123456789 1")
    uid, n = int(nums[0]), int(nums[1]) if len(nums) > 1 else 1
    db.execute("UPDATE users SET credits = COALESCE(credits, 0) + ? WHERE user_id=?", (n, uid))
    db.commit()
    await message.answer(f"✅ {uid} ga {n} ta savol qo'shildi.")
    try:
        lang = get_lang(uid)
        await bot.send_message(uid, T[lang]["pay_ok"], reply_markup=menu_kb(lang))
    except Exception:
        pass


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
    await start_calc(cb.message, state, lang, cb.from_user.id)


async def start_calc(message: Message, state: FSMContext, lang: str, uid: int):
    await state.clear()
    if not await ensure_sub(message, lang, uid):
        return
    await state.set_state(Calc.start_date)
    await message.answer(T[lang]["q1"])


@router.message(F.text.in_(CALC_BTNS))
async def btn_calc(message: Message, state: FSMContext):
    await start_calc(message, state, get_lang(message.from_user.id), message.from_user.id)


@router.message(F.text.in_(OTHER_BTNS))
async def btn_other(message: Message, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    lang = get_lang(uid)
    if is_admin(uid) or int(user_field(uid, "credits", 0)) > 0:
        return await message.answer(T[lang]["ask_question"])
    await show_payment(message, state, lang, uid)


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
async def free_question(message: Message, bot: Bot, state: FSMContext):
    uid = message.from_user.id
    if not has_lang(uid):
        save_user(message)
        return await message.answer(CHOOSE_LANG, reply_markup=lang_kb())
    lang = get_lang(uid)
    t = T[lang]
    if message.text.startswith("/"):
        return
    admin = is_admin(uid)
    if not admin and int(user_field(uid, "credits", 0)) <= 0:
        return await show_payment(message, state, lang, uid)
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
    if not admin and answer:
        db.execute("UPDATE users SET credits = MAX(credits - 1, 0) WHERE user_id=?", (uid,))
        db.commit()
        left = int(user_field(uid, "credits", 0))
        if left > 0:
            answer += t["credit_left"].format(n=left)
    await send_long(message, answer or t["error"], reply_markup=menu_kb(lang))


@router.message()
async def other_content(message: Message, bot: Bot, state: FSMContext):
    # Holatsiz yuborilgan rasm/fayl — ehtimol to'lov cheki
    if (message.photo or message.document) and not is_admin(message.from_user.id):
        return await handle_receipt(message, bot, state)
    await message.answer(T[get_lang(message.from_user.id)]["text_only"])


DP = Dispatcher()


async def main():
    bot = Bot(BOT_TOKEN)
    dp = DP
    bot.session.middleware(emoji_fallback)
    dp.include_router(admin_router)
    dp.include_router(paid_router)
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    log.info("Bot ishga tushdi. Model: %s", MODEL)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

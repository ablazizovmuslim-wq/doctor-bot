# Bot matnlari / Тексты бота.
# Matnni o'zgartirish uchun shu faylni tahrirlang.

WEEKDAYS = {
    "uz": ["dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba"],
    "ru": ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"],
}

CHOOSE_LANG = "Tilni tanlang 👇\nВыберите язык 👇"

T = {
    "uz": {
        "welcome": (
            "Assalomu alaykum! 👋\n"
            "Men shifokorning yordamchi botiman.\n\n"
            "Hozir ovulyatsiya kuningizni taxminiy hisoblab beraman. "
            "Buning uchun 3 ta savolga javob bering."
        ),
        "q1": (
            "1️⃣ Oxirgi hayzingiz qachon boshlangan?\n\n"
            "Sanani kun.oy ko'rinishida yozing, masalan: 05.11"
        ),
        "bad_date": "Sanani tushunmadim 🙏 Iltimos, kun.oy ko'rinishida yozing, masalan: 05.11 yoki 05.11.2026",
        "future_date": "Bu sana hali kelmagan 🙂 Oxirgi hayz boshlangan sanani yozing.",
        "old_date": "Bu sana juda eski (90 kundan ko'p). Iltimos, oxirgi hayz boshlangan sanani yozing.",
        "q2": (
            "2️⃣ Hayz sikli odatda necha kun bo'ladi?\n"
            "(bir hayz boshlangan kundan keyingi hayz boshlanguncha bo'lgan kunlar soni)\n\n"
            "Quyidan tanlang yoki raqam yozing 👇"
        ),
        "bad_cycle": "Iltimos, 20 dan 45 gacha bo'lgan raqam yozing, masalan: 28",
        "q3": "3️⃣ Hayz doim bir xil vaqtda keladimi? Kechikish yoki buzilishlar bo'lmaydimi?",
        "yes": "✅ Ha, doim bir xil",
        "no": "❌ Yo'q, o'zgarib turadi",
        "irregular": (
            "Hayz sikli o'zgarib tursa, ovulyatsiya kunini kalendar bo'yicha aniq hisoblab bo'lmaydi 🙏\n\n"
            "Bunday holatda shifokor ko'rigidan o'tish tavsiya etiladi. Ovulyatsiyani aniqlashda "
            "ultratovush tekshiruvi (follikulometriya) yoki ovulyatsiya testlari yordam beradi.\n\n"
            "Savolingiz bo'lsa, «❓ Boshqa savol» tugmasini bosib yozing."
        ),
        "late": (
            "⚠️ Hisob bo'yicha keyingi hayz {next} kuni boshlanishi kerak edi. "
            "Hozir {late} kun kechikish bor.\n\n"
            "Homiladorlik testini qilib ko'rish yoki shifokorga murojaat qilish tavsiya etiladi.\n\n"
            "Agar sanani xato kiritgan bo'lsangiz, «🗓 Ovulyatsiyani hisoblash» tugmasini bosib qaytadan kiriting."
        ),
        "result": (
            "📅 Natija (taxminiy):\n\n"
            "• Oxirgi hayz boshlangan: {start}\n"
            "• Sikl davomiyligi: {cycle} kun\n\n"
            "🥚 Ovulyatsiya kuni: {ov}\n"
            "🌸 Homilador bo'lish ehtimoli eng yuqori kunlar: {f1} — {f2}\n"
            "🩸 Keyingi hayz kutiladi: {next}"
            "{passed}\n\n"
            "ℹ️ Hisoblash usuli: keyingi hayz sanasidan 14 kun ayiriladi. "
            "Bu taxminiy natija. Aniqroq bilish uchun ovulyatsiya testi yoki UZI (follikulometriya) yordam beradi."
        ),
        "passed": "\n\n⏳ Bu sikldagi ovulyatsiya kuni o'tib ketgan. Keyingi sikldagi taxminiy ovulyatsiya: {ov2}",
        "after_result": "Yana savolingiz bo'lsa, «❓ Boshqa savol» tugmasini bosing.",
        "other_prompt": "✍️ Savolingizni yozing, javob beraman.",
        "limit": "Bugungi savollar limiti tugadi ({limit} ta). Ertaga yana yozing 🙏",
        "error": "Kechirasiz, hozir javob bera olmadim. Birozdan keyin qayta urinib ko'ring 🙏",
        "unavailable": "Kechirasiz, bot vaqtincha ishlamayapti. Keyinroq urinib ko'ring 🙏",
        "text_only": "Iltimos, savolingizni matn ko'rinishida yozing ✍️",
        "btn_calc": "🗓 Ovulyatsiyani hisoblash",
        "btn_other": "❓ Boshqa savol",
        "btn_lang": "🌐 Tilni o'zgartirish",
    },
    "ru": {
        "welcome": (
            "Здравствуйте! 👋\n"
            "Я бот-помощник врача.\n\n"
            "Сейчас я примерно рассчитаю день вашей овуляции. "
            "Для этого ответьте на 3 вопроса."
        ),
        "q1": (
            "1️⃣ Когда началась ваша последняя менструация?\n\n"
            "Напишите дату в формате день.месяц, например: 05.11"
        ),
        "bad_date": "Не понял дату 🙏 Напишите в формате день.месяц, например: 05.11 или 05.11.2026",
        "future_date": "Эта дата ещё не наступила 🙂 Напишите дату начала последней менструации.",
        "old_date": "Эта дата слишком давняя (больше 90 дней). Напишите дату начала последней менструации.",
        "q2": (
            "2️⃣ Сколько дней обычно длится ваш цикл?\n"
            "(число дней от начала одной менструации до начала следующей)\n\n"
            "Выберите ниже или напишите число 👇"
        ),
        "bad_cycle": "Пожалуйста, напишите число от 20 до 45, например: 28",
        "q3": "3️⃣ Менструация всегда приходит регулярно? Без задержек и сбоев?",
        "yes": "✅ Да, всегда регулярно",
        "no": "❌ Нет, бывает по-разному",
        "irregular": (
            "При нерегулярном цикле точно рассчитать день овуляции по календарю нельзя 🙏\n\n"
            "В таком случае рекомендуется пройти осмотр у врача. Определить овуляцию помогают "
            "УЗИ (фолликулометрия) или тесты на овуляцию.\n\n"
            "Если есть вопросы, нажмите «❓ Другой вопрос» и напишите."
        ),
        "late": (
            "⚠️ По расчёту следующая менструация должна была начаться {next}. "
            "Сейчас задержка {late} дн.\n\n"
            "Рекомендуется сделать тест на беременность или обратиться к врачу.\n\n"
            "Если вы ошиблись с датой, нажмите «🗓 Рассчитать овуляцию» и введите заново."
        ),
        "result": (
            "📅 Результат (примерный):\n\n"
            "• Начало последней менструации: {start}\n"
            "• Длина цикла: {cycle} дн.\n\n"
            "🥚 День овуляции: {ov}\n"
            "🌸 Дни с наибольшей вероятностью зачатия: {f1} — {f2}\n"
            "🩸 Следующая менструация ожидается: {next}"
            "{passed}\n\n"
            "ℹ️ Как считается: от даты следующей менструации отнимается 14 дней. "
            "Это примерный результат. Точнее определить помогут тест на овуляцию или УЗИ (фолликулометрия)."
        ),
        "passed": "\n\n⏳ Овуляция в этом цикле уже прошла. Примерная овуляция в следующем цикле: {ov2}",
        "after_result": "Если есть ещё вопросы, нажмите «❓ Другой вопрос».",
        "other_prompt": "✍️ Напишите ваш вопрос, я отвечу.",
        "limit": "Лимит вопросов на сегодня исчерпан ({limit}). Напишите завтра 🙏",
        "error": "Извините, сейчас не получилось ответить. Попробуйте чуть позже 🙏",
        "unavailable": "Извините, бот временно не работает. Попробуйте позже 🙏",
        "text_only": "Пожалуйста, напишите вопрос текстом ✍️",
        "btn_calc": "🗓 Рассчитать овуляцию",
        "btn_other": "❓ Другой вопрос",
        "btn_lang": "🌐 Сменить язык",
    },
}

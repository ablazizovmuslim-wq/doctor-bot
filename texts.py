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
        # --- Instagram obuna ---
        "sub_need": (
            "📸 Ovulyatsiya kunini hisoblash shifokorning Instagram sahifasiga obuna bo'lganlar uchun bepul.\n\n"
            "1) Quyidagi tugma orqali sahifaga o'ting va obuna bo'ling.\n"
            "2) «✅ Obuna bo'ldim» tugmasini bosing.\n\n"
            "🎁 Obunachilarga savollar 50% chegirma bilan!"
        ),
        "btn_insta": "📸 Instagram sahifasi",
        "btn_subbed": "✅ Obuna bo'ldim",
        "ask_ig": "Instagram username'ingizni yozing (masalan: madina_01)",
        "bad_ig": "Username'ni tushunmadim 🙏 Masalan: madina_01",
        "sub_sent": "⏳ So'rovingiz yuborildi. Obunangiz tekshirilgach, sizga xabar keladi.",
        "sub_pending": "⏳ So'rovingiz tekshirilmoqda. Tasdiqlangach, sizga xabar keladi.",
        "sub_ok": "✅ Obunangiz tasdiqlandi! Rahmat 🌸\n\nEndi ovulyatsiyani hisoblashingiz mumkin. Savollar siz uchun 50% chegirma bilan.",
        "sub_no": "❌ Obuna topilmadi. Iltimos, Instagram sahifaga obuna bo'lib, qaytadan «✅ Obuna bo'ldim» tugmasini bosing.",
        # --- Pullik savol ---
        "pay_info": (
            "❓ Shaxsiy savolingizga to'liq javob olish narxi: {price} so'm{discount}\n\n"
            "💳 Karta: {card}\n"
            "👤 {holder}\n\n"
            "To'lovni qilgach, chekni (skrinshot) shu yerga yuboring 👇"
        ),
        "pay_discount": " (obunachilar uchun 50% chegirma 🎁)",
        "pay_sub_hint": "🎁 Instagram sahifaga obuna bo'lsangiz, narx {sub_price} so'm bo'ladi.",
        "btn_get_discount": "🎁 Obuna bo'lib 50% chegirma olish",
        "pay_not_ready": "Kechirasiz, to'lov hozircha sozlanmagan. Keyinroq urinib ko'ring 🙏",
        "pay_need_photo": "Iltimos, to'lov chekini rasm (skrinshot) ko'rinishida yuboring 📸",
        "pay_sent": "⏳ Chek yuborildi. To'lov tasdiqlangach, sizga xabar keladi va savolingizni yozasiz.",
        "pay_pending": "⏳ To'lovingiz tekshirilmoqda. Tasdiqlangach, sizga xabar keladi.",
        "pay_ok": "✅ To'lov tasdiqlandi! Rahmat 🌸\n\nEndi savolingizni batafsil yozing ✍️",
        "pay_no": "❌ To'lov topilmadi. Agar to'lagan bo'lsangiz, chekni qaytadan yuboring.",
        "ask_question": "✍️ Savolingizni batafsil yozing, to'liq javob beraman.",
        "credit_left": "\n\n💬 Qolgan savollar: {n}",
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
        # --- Подписка Instagram ---
        "sub_need": (
            "📸 Расчёт дня овуляции бесплатный для подписчиков Instagram-страницы врача.\n\n"
            "1) Перейдите на страницу по кнопке ниже и подпишитесь.\n"
            "2) Нажмите «✅ Я подписался(ась)».\n\n"
            "🎁 Для подписчиков вопросы со скидкой 50%!"
        ),
        "btn_insta": "📸 Страница в Instagram",
        "btn_subbed": "✅ Я подписался(ась)",
        "ask_ig": "Напишите ваш username в Instagram (например: madina_01)",
        "bad_ig": "Не понял username 🙏 Например: madina_01",
        "sub_sent": "⏳ Запрос отправлен. После проверки подписки вам придёт сообщение.",
        "sub_pending": "⏳ Ваш запрос проверяется. После подтверждения вам придёт сообщение.",
        "sub_ok": "✅ Подписка подтверждена! Спасибо 🌸\n\nТеперь вы можете рассчитать овуляцию. Вопросы для вас со скидкой 50%.",
        "sub_no": "❌ Подписка не найдена. Подпишитесь на страницу в Instagram и снова нажмите «✅ Я подписался(ась)».",
        # --- Платный вопрос ---
        "pay_info": (
            "❓ Полный ответ на ваш личный вопрос стоит: {price} сум{discount}\n\n"
            "💳 Карта: {card}\n"
            "👤 {holder}\n\n"
            "После оплаты отправьте сюда чек (скриншот) 👇"
        ),
        "pay_discount": " (скидка 50% для подписчиков 🎁)",
        "pay_sub_hint": "🎁 Если подпишетесь на страницу в Instagram, цена будет {sub_price} сум.",
        "btn_get_discount": "🎁 Подписаться и получить скидку 50%",
        "pay_not_ready": "Извините, оплата пока не настроена. Попробуйте позже 🙏",
        "pay_need_photo": "Пожалуйста, отправьте чек об оплате в виде фото (скриншота) 📸",
        "pay_sent": "⏳ Чек отправлен. После подтверждения оплаты вам придёт сообщение, и вы напишете вопрос.",
        "pay_pending": "⏳ Ваша оплата проверяется. После подтверждения вам придёт сообщение.",
        "pay_ok": "✅ Оплата подтверждена! Спасибо 🌸\n\nТеперь подробно напишите ваш вопрос ✍️",
        "pay_no": "❌ Оплата не найдена. Если вы оплатили, отправьте чек ещё раз.",
        "ask_question": "✍️ Подробно напишите ваш вопрос, я дам полный ответ.",
        "credit_left": "\n\n💬 Осталось вопросов: {n}",
    },
}

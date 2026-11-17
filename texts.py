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
            "Ovulyatsiya kuningizni hisoblab beraman va savollaringizga javob beraman.\n\n"
            "🎁 Shifokorning Instagram sahifasiga obuna bo'lsangiz — chegirma!"
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
            "Bu taxminiy natija. Aniqroq bilish uchun ovulyatsiya testi yoki UZI (follikulometriya) yordam beradi.\n\n"
            "⚠️ Agar hayz kechikib yoki o'zgarib tursa, kalendar hisobi aniq bo'lmaydi — "
            "bunday holatda shifokor ko'rigi, follikulometriya yoki ovulyatsiya testlari tavsiya etiladi."
        ),
        "passed": "\n\n⏳ Bu sikldagi ovulyatsiya kuni o'tib ketgan. Keyingi sikldagi taxminiy ovulyatsiya: {ov2}",
        "after_result": "Yana savolingiz bo'lsa, «❓ Boshqa savol» tugmasini bosing.",
        "other_prompt": "✍️ Savolingizni yozing, javob beraman.\n📷 Rasm (tahlil, UZI), PDF yoki video ham yuborishingiz mumkin.",
        "limit": "Bugungi savollar limiti tugadi ({limit} ta). Ertaga yana yozing 🙏",
        "error": "Kechirasiz, hozir javob bera olmadim. Birozdan keyin qayta urinib ko'ring 🙏",
        "unavailable": "Kechirasiz, bot vaqtincha ishlamayapti. Keyinroq urinib ko'ring 🙏",
        "text_only": "Iltimos, savolingizni matn ko'rinishida yozing ✍️",
        "ai_note": "\n\n———\n🤖 Bu javobni sun'iy intellekt (AI) berdi. Unda xato bo'lishi mumkin — aniq tashxis va davolash uchun albatta shifokor bilan tekshirib oling.",
        "voice_no": "🎤 Ovozli xabarni hozircha tushunmayman. Savolingizni matn bilan yozing yoki rasm/video yuboring ✍️",
        "media_big": "📦 Fayl juda katta (20 MB dan ortiq). Kichikroq video yoki rasm yuboring 🙏",
        "media_unsupported": "Bu turdagi faylni o'qiy olmayman 🙏 Rasm, PDF yoki video yuboring, yoki matn bilan yozing.",
        "media_no_caption": "Mijoz izohsiz fayl yubordi. Unda nima ko'rinayotganini tushuntir va nima bezovta qilayotganini so'ra.",
        "btn_calc": "🗓 Ovulyatsiyani hisoblash",
        "btn_other": "❓ Boshqa savol",
        "btn_lang": "🌐 Tilni o'zgartirish",
        # --- Instagram obuna ---
        "sub_need": (
            "📸 Ovulyatsiya kunini hisoblash shifokorning Instagram sahifasiga obuna bo'lganlar uchun bepul.\n\n"
            "1) Quyidagi tugma orqali sahifaga o'ting va obuna bo'ling.\n"
            "2) «✅ Obuna bo'ldim» tugmasini bosing.\n\n"
            "🎁 Obunachilarga chegirma!"
        ),
        "btn_insta": "📸 Instagram sahifasi",
        "btn_subbed": "✅ Obuna bo'ldim",
        "ask_ig": "Instagram username'ingizni yozing (masalan: madina_01)",
        "bad_ig": "Username'ni tushunmadim 🙏 Masalan: madina_01",
        "sub_sent": "⏳ So'rovingiz yuborildi. Obunangiz tekshirilgach, sizga xabar keladi.",
        "sub_pending": "⏳ So'rovingiz tekshirilmoqda. Tasdiqlangach, sizga xabar keladi.",
        "sub_ok": "✅ Obunangiz tasdiqlandi! Rahmat 🌸\n\nEndi ovulyatsiyani hisoblash va savollar siz uchun chegirma bilan — 5 000 so'mdan. Kerakli tugmani qayta bosing 👇",
        "sub_no": "❌ Obuna topilmadi. Iltimos, Instagram sahifaga obuna bo'lib, qaytadan «✅ Obuna bo'ldim» tugmasini bosing.",
        # --- Pullik savol ---
        "pay_info": (
            "❓ {n} ta savolingizga to'liq javob olish narxi: {price} so'm{discount}\n\n"
            "💳 Karta: {card}\n"
            "👤 {holder}\n\n"
            "To'lovni qilgach, chekni (skrinshot) shu yerga yuboring 👇"
        ),
        "pay_discount": " (obunachilar uchun chegirma 🎁)",
        "pay_sub_hint": (
            "🎁 {sub_price} so'mga (chegirma bilan) olish uchun, iltimos, "
            "quyidagi havola orqali o'tib, shifokorning Instagram sahifasiga obuna bo'ling, "
            "so'ng «✅ Obuna bo'ldim» tugmasini bosing 👇"
        ),
        "btn_insta_go": "📸 Instagram'ga o'tib obuna bo'lish",
        "btn_pay_calc": "💳 {price} so'm to'lab hisoblash",
        "sub_or_pay": "💳 Yoki obuna bo'lmasdan, {price} so'm to'lab hisoblatishingiz mumkin.",
        "pay_info_calc": (
            "🗓 Ovulyatsiya kunini hisoblash narxi: {price} so'm{discount}\n\n"
            "💳 Karta: {card}\n"
            "👤 {holder}\n\n"
            "To'lovni qilgach, chekni (skrinshot) shu yerga yuboring 👇"
        ),
        "pay_ok_calc": "✅ To'lov tasdiqlandi! Rahmat 🌸\n\nEndi «🗓 Ovulyatsiyani hisoblash» tugmasini bosing.",
        "btn_get_discount": "🎁 Obuna bo'lib chegirma olish",
        "pay_not_ready": "Kechirasiz, to'lov hozircha sozlanmagan. Keyinroq urinib ko'ring 🙏",
        "pay_need_photo": "Iltimos, to'lov chekini rasm (skrinshot) ko'rinishida yuboring 📸",
        "pay_sent": "⏳ Chek yuborildi. To'lov tasdiqlangach, sizga xabar keladi.",
        "pay_pending": "⏳ To'lovingiz tekshirilmoqda. Tasdiqlangach, sizga xabar keladi.",
        "pay_ok": "✅ To'lov tasdiqlandi! Rahmat 🌸\n\nSizda {n} ta savol bor. Birinchi savolingizni batafsil yozing ✍️",
        "pay_no": "❌ To'lov topilmadi. Agar to'lagan bo'lsangiz, chekni qaytadan yuboring.",
        "ask_question": "✍️ Savolingizni batafsil yozing, to'liq javob beraman.",
        "credit_left": "\n\n💬 Qolgan savollar: {n}",
        # --- Paketlar ---
        "btn_pkgs": "💎 Paketlar",
        "sum": "so'm",
        "pkg_once": "❓ Savol-javob",
        "pkg_day": "☀️ Kunlik",
        "pkg_week": "📅 Haftalik",
        "pkg_month": "🌙 Oylik",
        "pkg_vip": "👑 VIP yillik",
        "pkgd_once": "3 ta savol + 1 ta ovulyatsiya hisoblash",
        "pkgd_day": "1 kun — savollar va hisoblash cheksiz",
        "pkgd_week": "7 kun — savollar va hisoblash cheksiz",
        "pkgd_month": "30 kun — savollar va hisoblash cheksiz",
        "pkgd_vip": "365 kun — savollar va hisoblash cheksiz",
        "pkgs_title": "💎 <b>Paketni tanlang:</b>",
        "pkgs_sub_on": "🎁 Siz Instagram obunachisisiz — barcha paketlar chegirma bilan!",
        "pkgs_sub_hint": "🎁 Shifokorning Instagram sahifasiga obuna bo'lsangiz — <b>barcha paketlar chegirma bilan</b>. Obuna bo'lib, «✅ Obuna bo'ldim» ni bosing 👇",
        "need_q": "❓ Savolingizga javob olish uchun to'lov qiling.",
        "start_offer": "📸 Shifokorning Instagram sahifasiga obuna bo'ling va javobni <b>chegirma bilan</b> oling — yoki <b>10 000 so'm</b> to'lab javob oling 👇",
        "need_calc": "🗓 Ovulyatsiya kunini hisoblash uchun to'lov qiling.",
        "pkgs_sub_hint_one": "🎁 Shifokorning Instagram sahifasiga obuna bo'lsangiz — atigi <b>{sub_price} so'm</b>! Obuna bo'lib, «✅ Obuna bo'ldim» ni bosing 👇",
        "pay_info_pkg": (
            "💎 Paket: <b>{name}</b>\n"
            "📦 {what}\n"
            "💵 Narx: <b>{price} so'm</b>{discount}\n\n"
            "💳 Karta: {card}\n"
            "👤 {holder}\n\n"
            "To'lovni qilgach, chekni (skrinshot) shu yerga yuboring 👇"
        ),
        "pay_ok_once": "✅ To'lov tasdiqlandi! Rahmat 🌸\n\nSizda {q} ta savol va {c} ta ovulyatsiya hisoblash bor. Kerakli tugmani bosing 👇",
        "pay_ok_vip": "✅ To'lov tasdiqlandi! Rahmat 🌸\n\n💎 {name} paket faollashdi: <b>{until}</b> gacha savollar va hisoblash cheksiz (kuniga {limit} tagacha savol).",
        "vip_left": "\n\n💎 Paketingiz {until} gacha faol",
    },
    "ru": {
        "welcome": (
            "Здравствуйте! 👋\n"
            "Я бот-помощник врача.\n\n"
            "Я рассчитаю день вашей овуляции и отвечу на ваши вопросы.\n\n"
            "🎁 Подпишитесь на Instagram-страницу врача — скидка!"
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
            "Это примерный результат. Точнее определить помогут тест на овуляцию или УЗИ (фолликулометрия).\n\n"
            "⚠️ Если менструация бывает с задержками или нерегулярно, календарный расчёт неточен — "
            "в таком случае рекомендуется осмотр врача, фолликулометрия или тесты на овуляцию."
        ),
        "passed": "\n\n⏳ Овуляция в этом цикле уже прошла. Примерная овуляция в следующем цикле: {ov2}",
        "after_result": "Если есть ещё вопросы, нажмите «❓ Другой вопрос».",
        "other_prompt": "✍️ Напишите ваш вопрос, я отвечу.\n📷 Можно также отправить фото (анализы, УЗИ), PDF или видео.",
        "limit": "Лимит вопросов на сегодня исчерпан ({limit}). Напишите завтра 🙏",
        "error": "Извините, сейчас не получилось ответить. Попробуйте чуть позже 🙏",
        "unavailable": "Извините, бот временно не работает. Попробуйте позже 🙏",
        "text_only": "Пожалуйста, напишите вопрос текстом ✍️",
        "ai_note": "\n\n———\n🤖 Этот ответ дал искусственный интеллект (ИИ). В нём возможны ошибки — для точного диагноза и лечения обязательно проверьте у врача.",
        "voice_no": "🎤 Голосовые сообщения пока не понимаю. Напишите вопрос текстом или отправьте фото/видео ✍️",
        "media_big": "📦 Файл слишком большой (больше 20 МБ). Отправьте видео или фото поменьше 🙏",
        "media_unsupported": "Не могу прочитать такой файл 🙏 Отправьте фото, PDF или видео, либо напишите текстом.",
        "media_no_caption": "Клиент прислал файл без подписи. Объясни, что на нём видно, и спроси, что его беспокоит.",
        "btn_calc": "🗓 Рассчитать овуляцию",
        "btn_other": "❓ Другой вопрос",
        "btn_lang": "🌐 Сменить язык",
        # --- Подписка Instagram ---
        "sub_need": (
            "📸 Расчёт дня овуляции бесплатный для подписчиков Instagram-страницы врача.\n\n"
            "1) Перейдите на страницу по кнопке ниже и подпишитесь.\n"
            "2) Нажмите «✅ Я подписался(ась)».\n\n"
            "🎁 Для подписчиков скидка!"
        ),
        "btn_insta": "📸 Страница в Instagram",
        "btn_subbed": "✅ Я подписался(ась)",
        "ask_ig": "Напишите ваш username в Instagram (например: madina_01)",
        "bad_ig": "Не понял username 🙏 Например: madina_01",
        "sub_sent": "⏳ Запрос отправлен. После проверки подписки вам придёт сообщение.",
        "sub_pending": "⏳ Ваш запрос проверяется. После подтверждения вам придёт сообщение.",
        "sub_ok": "✅ Подписка подтверждена! Спасибо 🌸\n\nТеперь расчёт овуляции и вопросы для вас со скидкой — от 5 000 сум. Нажмите нужную кнопку ещё раз 👇",
        "sub_no": "❌ Подписка не найдена. Подпишитесь на страницу в Instagram и снова нажмите «✅ Я подписался(ась)».",
        # --- Платный вопрос ---
        "pay_info": (
            "❓ Полные ответы на {n} ваших вопроса: {price} сум{discount}\n\n"
            "💳 Карта: {card}\n"
            "👤 {holder}\n\n"
            "После оплаты отправьте сюда чек (скриншот) 👇"
        ),
        "pay_discount": " (скидка для подписчиков 🎁)",
        "pay_sub_hint": (
            "🎁 Чтобы получить за {sub_price} сум (со скидкой), пожалуйста, "
            "перейдите по ссылке ниже и подпишитесь на Instagram-страницу врача, "
            "затем нажмите «✅ Я подписался(ась)» 👇"
        ),
        "btn_insta_go": "📸 Перейти в Instagram и подписаться",
        "btn_pay_calc": "💳 Оплатить {price} сум и рассчитать",
        "sub_or_pay": "💳 Или без подписки — оплатите {price} сум и получите расчёт.",
        "pay_info_calc": (
            "🗓 Стоимость расчёта дня овуляции: {price} сум{discount}\n\n"
            "💳 Карта: {card}\n"
            "👤 {holder}\n\n"
            "После оплаты отправьте сюда чек (скриншот) 👇"
        ),
        "pay_ok_calc": "✅ Оплата подтверждена! Спасибо 🌸\n\nТеперь нажмите «🗓 Рассчитать овуляцию».",
        "btn_get_discount": "🎁 Подписаться и получить скидку",
        "pay_not_ready": "Извините, оплата пока не настроена. Попробуйте позже 🙏",
        "pay_need_photo": "Пожалуйста, отправьте чек об оплате в виде фото (скриншота) 📸",
        "pay_sent": "⏳ Чек отправлен. После подтверждения оплаты вам придёт сообщение.",
        "pay_pending": "⏳ Ваша оплата проверяется. После подтверждения вам придёт сообщение.",
        "pay_ok": "✅ Оплата подтверждена! Спасибо 🌸\n\nУ вас {n} вопроса. Подробно напишите первый вопрос ✍️",
        "pay_no": "❌ Оплата не найдена. Если вы оплатили, отправьте чек ещё раз.",
        "ask_question": "✍️ Подробно напишите ваш вопрос, я дам полный ответ.",
        "credit_left": "\n\n💬 Осталось вопросов: {n}",
        # --- Пакеты ---
        "btn_pkgs": "💎 Пакеты",
        "sum": "сум",
        "pkg_once": "❓ Вопрос-ответ",
        "pkg_day": "☀️ На день",
        "pkg_week": "📅 На неделю",
        "pkg_month": "🌙 На месяц",
        "pkg_vip": "👑 VIP на год",
        "pkgd_once": "3 вопроса + 1 расчёт овуляции",
        "pkgd_day": "1 день — вопросы и расчёты без ограничений",
        "pkgd_week": "7 дней — вопросы и расчёты без ограничений",
        "pkgd_month": "30 дней — вопросы и расчёты без ограничений",
        "pkgd_vip": "365 дней — вопросы и расчёты без ограничений",
        "pkgs_title": "💎 <b>Выберите пакет:</b>",
        "pkgs_sub_on": "🎁 Вы подписчик Instagram — все пакеты со скидкой!",
        "pkgs_sub_hint": "🎁 Подпишитесь на Instagram-страницу врача — <b>все пакеты со скидкой</b>. После подписки нажмите «✅ Я подписался(ась)» 👇",
        "need_q": "❓ Чтобы получить ответ на вопрос, оплатите.",
        "start_offer": "📸 Подпишитесь на Instagram-страницу врача и получите ответ <b>со скидкой</b> — или оплатите <b>10 000 сум</b> 👇",
        "need_calc": "🗓 Для расчёта дня овуляции оплатите.",
        "pkgs_sub_hint_one": "🎁 Подпишитесь на Instagram-страницу врача — всего <b>{sub_price} сум</b>! После подписки нажмите «✅ Я подписался(ась)» 👇",
        "pay_info_pkg": (
            "💎 Пакет: <b>{name}</b>\n"
            "📦 {what}\n"
            "💵 Цена: <b>{price} сум</b>{discount}\n\n"
            "💳 Карта: {card}\n"
            "👤 {holder}\n\n"
            "После оплаты отправьте сюда чек (скриншот) 👇"
        ),
        "pay_ok_once": "✅ Оплата подтверждена! Спасибо 🌸\n\nУ вас {q} вопроса и {c} расчёт овуляции. Нажмите нужную кнопку 👇",
        "pay_ok_vip": "✅ Оплата подтверждена! Спасибо 🌸\n\n💎 Пакет {name} активен: до <b>{until}</b> вопросы и расчёты без ограничений (до {limit} вопросов в день).",
        "vip_left": "\n\n💎 Ваш пакет активен до {until}",
    },
}

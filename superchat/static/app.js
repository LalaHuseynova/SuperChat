"use strict";
const $ = (s) => document.querySelector(s);
const icons = {
  plus: "M12 5v14M5 12h14",
  trash: "M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7",
  search: "M21 21l-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0",
  plane: "m22 2-7 20-4-9-9-4 20-7ZM22 2 11 13",
  bag: "M5 7h14l1 14H4L5 7Zm3 0V5a4 4 0 0 1 8 0v2",
  film: "M4 3h16v18H4V3ZM8 3v18M16 3v18M4 8h4M4 16h4M16 8h4M16 16h4M8 12h8",
  shield: "m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Zm-4 9 3 3 5-6",
  settings:
    "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm0-6v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2",
  globe:
    "M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM3 12h18M12 3c-5 5-5 13 0 18 5-5 5-13 0-18",
  panel: "M3 4h18v16H3V4ZM15 4v16",
  sparkle: "m12 2 3 7 7 3-7 3-3 7-3-7-7-3 7-3Z",
  ticket: "M3 6h18v4a2 2 0 0 0 0 4v4H3v-4a2 2 0 0 0 0-4V6Zm13 0v3m0 2v2m0 2v3",
  history: "M3 11a9 9 0 1 1 3 8M3 4v7h7m2-4v5l4 3",
  calendar: "M4 5h16v16H4V5Zm0 5h16M8 3v4m8-4v4",
  download: "M12 3v12m-5-5 5 5 5-5M4 15v6h16v-6",
  branch: "M7 3v12a4 4 0 0 0 4 4h6M7 8h5a5 5 0 0 0 5-5m-3 13 3 3-3 3",
  image: "M3 3h18v18H3V3Zm0 14 6-6 5 5 3-3 4 4M16 7h.01",
  mic: "M9 5a3 3 0 0 1 6 0v7a3 3 0 0 1-6 0V5ZM5 10v2a7 7 0 0 0 14 0v-2M12 19v3m-4 0h8",
  arrow: "M12 20V4m-6 6 6-6 6 6",
  menu: "M4 6h16M4 12h16M4 18h16",
  chat: "M3 4h18v13H9l-6 4V4",
  check: "m5 12 4 4L19 6",
  headphones: "M4 14V11a8 8 0 0 1 16 0v3M4 12h3v8H4v-8Zm13 0h3v8h-3v-8",
};
function icon(name) {
  return `<span class="icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="${icons[name] || icons.sparkle}"/></svg></span>`;
}
function fillIcons() {
  document.querySelectorAll("[data-icon]").forEach((el) => {
    el.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${icons[el.dataset.icon] || icons.sparkle}"/></svg>`;
  });
}
const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const lex = {
  deleteChat: ["Delete chat", "Söhbəti sil", "Удалить чат"],
  deleteHeading: ["Delete this conversation?", "Bu söhbət silinsin?", "Удалить этот разговор?"],
  deleteDescription: ["Messages, shopping list, saved plans and the chat log will be permanently deleted.", "Mesajlar, alış-veriş siyahısı, saxlanılmış planlar və söhbət jurnalı həmişəlik silinəcək.", "Сообщения, список покупок, сохранённые планы и журнал чата будут удалены навсегда."],
  deleteWarning: ["This cannot be undone.", "Bunu geri qaytarmaq mümkün deyil.", "Это действие нельзя отменить."],
  keepChat: ["Cancel", "Ləğv et", "Отмена"],
  deleteChatConfirm: [
    'Delete “{title}”? Its messages, shopping list, saved plans and chat log will be permanently removed. This cannot be undone.',
    '“{title}” söhbəti silinsin? Mesajlar, alış-veriş siyahısı, saxlanılmış planlar və söhbət jurnalı həmişəlik silinəcək. Bunu geri qaytarmaq mümkün deyil.',
    'Удалить чат «{title}»? Сообщения, список покупок, сохранённые планы и журнал чата будут удалены навсегда. Это действие нельзя отменить.',
  ],
  workspace: ["Personal workspace", "Şəxsi məkan", "Личное пространство"],
  localWorkspace: [
    "Saved on this device",
    "Bu cihazda saxlanılır",
    "Сохранено на этом устройстве",
  ],
  newChat: ["New conversation", "Yeni söhbət", "Новый разговор"],
  recent: ["YOUR CONVERSATIONS", "SÖHBƏTLƏRİNİZ", "ВАШИ РАЗГОВОРЫ"],
  memoryTitle: [
    "A little continuity.",
    "Söhbətimiz davam edir.",
    "Продолжим разговор.",
  ],
  memoryDesc: [
    "Your conversations are saved, so you can pick up where you left off.",
    "Söhbətlər saxlanılır. Qaldığınız yerdən davam edin.",
    "Разговоры сохраняются. Продолжайте с того же места.",
  ],
  yourSpace: ["Your space", "Sizin məkanınız", "Ваше пространство"],
  assistant: ["Your assistant", "Sizin köməkçiniz", "Ваш помощник"],
  demo: ["DEMO", "DEMO", "ДЕМО"],
  saved: ["All changes saved", "Hər şey saxlanıldı", "Всё сохранено"],
  saving: ["Saving…", "Saxlanılır…", "Сохранение…"],
  welcomeKicker: [
    "A LITTLE LESS SEARCHING. A LITTLE MORE LIVING.",
    "DAHA AZ AXTARIŞ. HƏYATA DAHA ÇOX VAXT.",
    "МЕНЬШЕ ПОИСКОВ. БОЛЬШЕ ЖИЗНИ.",
  ],
  welcomeTitle: [
    "What’s on your<br>mind today?",
    "Bu gün nə<br>düşünürsünüz?",
    "Какие планы<br>на сегодня?",
  ],
  welcomeSubtitle: [
    "A weekend away. Your next good find. A night at the movies.<br>Bring it all here — we’ll take it one conversation at a time.",
    "Həftəsonu səfəri. Uğurlu alış-veriş. Kino axşamı.<br>Hamısını burada, bir söhbətdə planlaşdıraq.",
    "Поездка на выходные. Удачная покупка. Вечер в кино.<br>Обсудим всё здесь, в одном разговоре.",
  ],
  flightTitle: [
    "A change of scenery",
    "Yeni yerlər kəşf edin",
    "Сменить обстановку",
  ],
  flightPrompt: [
    "Find a flight to Istanbul<br>this Friday",
    "Bu cümə İstanbula<br>uçuş tapın",
    "Рейс в Стамбул<br>в эту пятницу",
  ],
  shoppingTitle: ["Something just right", "Tam sizə uyğun", "То, что нужно"],
  shoppingPrompt: [
    "iPhone 17 Pro",
    "iPhone 17 Pro",
    "iPhone 17 Pro",
  ],
  cinemaTitle: ["Make a night of it", "Kino axşamı", "Вечер в кино"],
  cinemaPrompt: [
    "What’s playing at the<br>cinema tonight?",
    "Bu axşam kinoda<br>nə göstərilir?",
    "Что сегодня вечером<br>идёт в кино?",
  ],
  noSwitch: [
    "Three worlds. No switching apps.",
    "Üç dünya. Bir söhbət.",
    "Три мира. Одно приложение.",
  ],
  voiceHint: [
    "Type it. Say it. Show it.",
    "Yazın. Deyin. Göstərin.",
    "Напишите. Скажите. Покажите.",
  ],
  mockCaption: [
    "Answers from the demo catalogue. All bookings are simulated.",
    "Cavablar nümunə kataloqdandır. Bütün bronlar simulyasiyadır.",
    "Ответы из демокаталога. Все бронирования учебные.",
  ],
  enterHint: ["Enter to send", "Göndərmək üçün Enter", "Enter — отправить"],
  contextTitle: ["In this conversation", "Bu söhbətdə", "В этом разговоре"],
  contextIntro: [
    "A place for the little details, while you explore the big possibilities.",
    "Yeni imkanları araşdırarkən kiçik detalları burada saxlayırıq.",
    "Место для деталей, пока вы строите большие планы.",
  ],
  cart: ["Your cart", "Səbətiniz", "Ваша корзина"],
  bookings: ["Saved bookings", "Saxlanılmış bronlar", "Бронирования"],
  remembered: ["Where we left off", "Qaldığımız yer", "На чём остановились"],
  catalogueDate: ["Demo calendar", "Demo təqvimi", "Демокалендарь"],
  clockNote: [
    "“Today” and “Friday” follow the project’s demo calendar.",
    "“Bu gün” və “cümə” layihənin demo təqviminə əsaslanır.",
    "«Сегодня» и «пятница» определяются демокалендарём.",
  ],
  export: [
    "Export conversation log",
    "Söhbət jurnalını yüklə",
    "Скачать журнал разговора",
  ],
  continue: [
    "Start a new chat with this context",
    "Bu kontekstlə yeni söhbət aç",
    "Новый чат с этим контекстом",
  ],
  aboutTitle: [
    "A connected conversation.",
    "Hər şey bir söhbətdə.",
    "Всё в одном разговоре.",
  ],
  aboutCopy: [
    "Explore flights, shopping, and cinema in English, Azerbaijani, or Russian. Switch topics naturally — each topic keeps its own context.",
    "Uçuş, alış-veriş və kinonu Azərbaycan, ingilis və ya rus dilində araşdırın. Mövzunu dəyişin — hər mövzu öz kontekstini saxlayır.",
    "Ищите рейсы, товары и кино на русском, азербайджанском или английском. Меняйте темы — контекст каждой сохраняется.",
  ],
  logInfo: [
    "Conversations and mock actions are saved in local JSONL files. New chats start fresh; “Start a new chat with this context” explicitly copies search context. Images are not saved.",
    "Söhbətlər və nümunə əməliyyatlar yerli JSONL fayllarında saxlanılır. Yeni söhbət təmiz başlayır. Konteksti ayrıca köçürə bilərsiniz. Şəkillər saxlanılmır.",
    "Разговоры и учебные действия сохраняются в локальных JSONL-файлах. Новые чаты независимы; контекст можно перенести явно. Изображения не сохраняются.",
  ],
  readAloud: [
    "Read replies aloud",
    "Cavabları səsləndir",
    "Читать ответы вслух",
  ],
  voiceInfo: [
    "Hands-free voice uses your browser’s speech service and may need internet. Enable the microphone once; speech is sent automatically after a pause. Language support varies by browser.",
    "Səsli giriş brauzerin nitq xidmətindən istifadə edir və internet tələb edə bilər. Mikrofonu bir dəfə aktivləşdirin; fasilədən sonra nitq avtomatik göndərilir. Dil dəstəyi brauzerdən asılıdır.",
    "Голосовой ввод использует службу браузера и может требовать интернет. Включите микрофон один раз; после паузы речь отправляется автоматически. Поддержка языков зависит от браузера.",
  ],
  input: [
    "Ask anything about flights, shopping, or cinema…",
    "Uçuş, alış-veriş və ya kino barədə soruşun…",
    "Спросите о рейсах, покупках или кино…",
  ],
  search: ["Search conversations", "Söhbətlərdə axtar", "Поиск разговоров"],
  noChats: [
    "Your next adventure starts here.",
    "Növbəti macəranız burada başlayır.",
    "Здесь начинается что-то новое.",
  ],
  cartEmpty: [
    "Your next find belongs here.",
    "Növbəti tapıntınızın yeri buradadır.",
    "Здесь будет ваша находка.",
  ],
  cartHint: [
    "Ask me to add something you like.",
    "Bəyəndiyinizi əlavə etməyimi istəyin.",
    "Попросите добавить понравившийся товар.",
  ],
  bookingEmpty: [
    "Good plans, all in one place.",
    "Yaxşı planlar bir yerdə.",
    "Хорошие планы в одном месте.",
  ],
  bookingHint: [
    "Your mock reservations will appear here.",
    "Nümunə bronlarınız burada görünəcək.",
    "Здесь появятся учебные бронирования.",
  ],
  memoryEmpty: [
    "Nothing to remember just yet. Let’s start with what’s on your mind.",
    "Hələ yadda saxlanılacaq məlumat yoxdur. Söhbətə başlayaq.",
    "Пока нечего запоминать. Начнём с ваших планов.",
  ],
  flights: ["Flights", "Uçuşlar", "Рейсы"],
  shopping: ["Shopping", "Alış-veriş", "Покупки"],
  cinema: ["Cinema", "Kino", "Кино"],
  total: ["Total", "Cəmi", "Итого"],
  available: ["available", "mövcuddur", "доступно"],
  soldOut: ["Unavailable", "Mövcud deyil", "Недоступно"],
  reserve: ["Reserve", "Bron et", "Забронировать"],
  add: ["Add to cart", "Səbətə əlavə et", "В корзину"],
  source: ["View data source", "Məlumat mənbəyi", "Источник данных"],
  grounded: ["From the catalogue", "Kataloqdan", "Из каталога"],
  thinking: [
    "Checking the catalogue…",
    "Kataloq yoxlanılır…",
    "Проверяю каталог…",
  ],
  imageThinking: [
    "Looking at your photo. First local use may take a few minutes…",
    "Şəkil yoxlanılır. İlk yerli istifadə bir neçə dəqiqə çəkə bilər…",
    "Распознаю фото. Первый локальный запуск может занять несколько минут…",
  ],
  retry: ["Retry", "Yenidən sına", "Повторить"],
  networkError: [
    "Could not reach Bir SuperChat. Your message is kept — try again.",
    "Bir SuperChat-a qoşulmaq olmadı. Mesajınız saxlanılıb — yenidən sınayın.",
    "Не удалось связаться с Bir SuperChat. Сообщение сохранено — повторите попытку.",
  ],
  fallback: [
    "AI is unavailable. This reply used the offline assistant.",
    "AI əlçatan deyil. Bu cavab oflayn köməkçi ilə hazırlandı.",
    "ИИ недоступен. Ответ подготовлен офлайн-помощником.",
  ],
  authFailed: [
    "The AI provider rejected the connection credentials. This reply used the offline assistant.",
    "AI provayderi qoşulma məlumatlarını qəbul etmədi. Bu cavab oflayn köməkçi ilə hazırlandı.",
    "Провайдер ИИ отклонил данные доступа. Ответ подготовлен офлайн-помощником.",
  ],
  listening: [
    "Listening — speak naturally",
    "Dinləyirəm — rahat danışın",
    "Слушаю — говорите свободно",
  ],
  hearing: ["Hearing you…", "Sizi eşidirəm…", "Слушаю вас…"],
  voiceUnavailable: [
    "This browser does not support speech recognition. Try Chrome, or type your message.",
    "Bu brauzer nitq tanımanı dəstəkləmir. Chrome sınayın və ya mesaj yazın.",
    "Браузер не поддерживает распознавание речи. Используйте Chrome или введите сообщение.",
  ],
  voiceDenied: [
    "Microphone unavailable or permission denied. Enable microphone access in browser settings.",
    "Mikrofon əlçatan deyil və ya icazə verilməyib. Brauzer ayarlarını yoxlayın.",
    "Микрофон недоступен или доступ запрещён. Проверьте настройки браузера.",
  ],
  voiceNetwork: [
    "The browser speech service is unavailable. You can still type.",
    "Brauzerin nitq xidməti əlçatan deyil. Yaza bilərsiniz.",
    "Служба распознавания речи недоступна. Можно ввести текст.",
  ],
  inherited: [
    "Search context continued from:",
    "Axtarış konteksti buradan köçürülüb:",
    "Контекст поиска перенесён из:",
  ],
  offlineProvider: [
    "Offline assistant active.",
    "Oflayn köməkçi aktivdir.",
    "Работает офлайн-помощник.",
  ],
  aiProvider: [
    "AI is configured. Catalogue facts are verified against saved data.",
    "AI konfiqurasiya edilib. Kataloq məlumatları saxlanılmış məlumatlarla yoxlanılır.",
    "ИИ настроен. Факты каталога проверяются по сохранённым данным.",
  ],
  photoError: [
    "Choose a JPEG, PNG, or WebP image up to 8 MB.",
    "8 MB-dək JPEG, PNG və ya WebP şəkli seçin.",
    "Выберите JPEG, PNG или WebP размером до 8 МБ.",
  ],
  newTitle: ["New conversation", "Yeni söhbət", "Новый разговор"],
  comparison: ["Comparison", "Müqayisə", "Сравнение"],
  price: ["Price", "Qiymət", "Цена"],
  item: ["Option", "Seçim", "Вариант"],
  quantity: ["Quantity", "Say", "Количество"],
  continuedEmpty: [
    "Your earlier search context is ready. Continue with a follow-up.",
    "Əvvəlki axtarış kontekstiniz hazırdır. Söhbətə davam edin.",
    "Прежний контекст поиска готов. Продолжайте разговор.",
  ],
};
Object.assign(lex, {
  snapshotMode: ["SNAPSHOT", "SAXLANILMIŞ", "СНИМОК"],
  snapshotCaption: ["Saved real listings. Prices and availability need confirmation at the source.", "Saxlanılmış real elanlar. Qiymət və mövcudluğu mənbədən təsdiqləyin.", "Сохранённые предложения. Уточняйте цену и наличие у источника."],
  snapshotCart: ["Shopping list", "Alış-veriş siyahısı", "Список покупок"],
  snapshotTotal: ["Estimated total", "Təxmini cəm", "Примерная сумма"],
  snapshotClock: ["Current date", "Cari tarix", "Текущая дата"],
  snapshotClockNote: ["Relative dates use today's Asia/Baku calendar. Listings have their own collection dates.", "Nisbi tarixlər Bakı vaxtına əsaslanır. Elanların toplanma tarixləri ayrıdır.", "Относительные даты считаются по времени Баку. У предложений своя дата сбора."],
  snapshotBookingHint: ["Save a flight or cinema showtime here, then open its source to book. Saving does not reserve seats.", "Uçuşu və ya kino seansını burada saxlayın, sonra bron üçün mənbəni açın. Saxlamaq yerləri bron etmir.", "Сохраните рейс или сеанс здесь, затем откройте источник для бронирования. Сохранение не резервирует места."],
  savedPlans: ["Saved plans", "Saxlanılmış planlar", "Сохранённые планы"],
  savePlan: ["Save to plans", "Planlara əlavə et", "Сохранить в планах"],
  localPlan: ["Saved only — not booked", "Yalnız saxlanılıb — bron edilməyib", "Сохранено — не забронировано"],
  removePlan: ["Remove saved plan", "Saxlanılmış planı sil", "Удалить сохранённый план"],
  unknown: ["Not published", "Dərc edilməyib", "Не опубликовано"],
  unknownAvailability: ["Availability unverified", "Mövcudluq yoxlanılmayıb", "Наличие не проверено"],
  listedStock: ["Listed in stock", "Elana görə stokda", "В наличии по снимку"],
  sourceOpen: ["View source", "Mənbəni aç", "Открыть источник"],
  listAdd: ["Save to list", "Siyahıya əlavə et", "В список"],
  sourceText: ["Source text", "Mənbə mətni", "Текст источника"],
  en: ["English", "İngilis", "Английский"],
  az: ["Azerbaijani", "Azərbaycan", "Азербайджанский"],
  ru: ["Russian", "Rus", "Русский"],
  collected: ["Collected", "Toplanıb", "Собрано"],
  stale: ["Older snapshot — check current details", "Köhnə məlumat — cari vəziyyəti yoxlayın", "Старый снимок — проверьте актуальность"],
  expired: ["This departure/showtime has passed", "Bu uçuş/seans vaxtı keçib", "Время вылета/сеанса прошло"],
  conflict: ["Source prices disagree — confirm the price", "Mənbə qiymətləri fərqlidir — təsdiqləyin", "Цены источников расходятся — уточните цену"],
  nearby: ["Nearby airport/city search — check the route", "Yaxın şəhər/hava limanı — marşrutu yoxlayın", "Поиск рядом — проверьте город/аэропорт"],
  snapshotPrice: ["Saved price", "Saxlanılmış qiymət", "Цена из снимка"],
  returnPrice: ["Round-trip total", "Gediş-dönüş cəmi", "Цена туда и обратно"],
  showMore: ["Show more", "Daha çox", "Ещё результаты"],
  shown: ["Showing", "Göstərilir", "Показано"],
  of: ["of", "/", "из"],
  refine: ["Narrow your search to see other options.", "Digər seçimlər üçün axtarışı dəqiqləşdirin.", "Уточните поиск для других вариантов."],
});
const snapshotLabels = {demo: "snapshotMode", mockCaption: "snapshotCaption", cart: "snapshotCart", total: "snapshotTotal", catalogueDate: "snapshotClock", clockNote: "snapshotClockNote", bookingHint: "snapshotBookingHint", bookings: "savedPlans"};
Object.assign(lex, {
  databaseMode: ["REAL CATALOGUE", "REAL KATALOQ", "РЕАЛЬНЫЙ КАТАЛОГ"],
  databaseCaption: ["Collected listings and cached flight fares. Open the source to confirm current details.", "Toplanmış elanlar və keşlənmiş uçuş qiymətləri. Cari məlumatı mənbədən təsdiqləyin.", "Собранные предложения и кэшированные цены на рейсы. Уточняйте актуальность у источника."],
  similarity: ["Image similarity", "Şəkil oxşarlığı", "Сходство изображений"],
  birmarketOpen: ["Open Birmarket", "Birmarket-də aç", "Открыть Birmarket"],
  cinemaOpen: ["Open CinemaPlus", "CinemaPlus-da aç", "Открыть CinemaPlus"],
  flightOpen: ["Open Aviasales", "Aviasales-də aç", "Открыть Aviasales"],
  cachedFare: ["Cached fare — confirm on Aviasales", "Keşlənmiş qiymət — Aviasales-də təsdiqləyin", "Кэшированная цена — уточните на Aviasales"],
});
const fieldNames = {
  trip_type: ["Itinerary", "Marşrut növü", "Тип поездки"],
  return_date: ["Return date", "Dönüş tarixi", "Дата возвращения"],
  departure: ["Departure", "Uçuş vaxtı", "Вылет"],
  arrival: ["Arrival", "Eniş vaxtı", "Прилёт"],
  duration: ["Duration (min)", "Müddət (dəq)", "Время (мин)"],
  stops: ["Stops", "Dayanacaq", "Пересадки"],
  baggage: ["Baggage (kg)", "Baqaj (kq)", "Багаж (кг)"],
  cabin: ["Cabin", "Sinif", "Класс"],
  via: ["Via", "Vasitəsilə", "Через"],
  description: ["Details", "Məlumat", "Описание"],
  color: ["Colour", "Rəng", "Цвет"],
  rating: ["Rating", "Reytinq", "Рейтинг"],
  category: ["Category", "Kateqoriya", "Категория"],
  date: ["Date", "Tarix", "Дата"],
  time: ["Time", "Vaxt", "Время"],
  language: ["Language", "Dil", "Язык"],
  age: ["Age rating", "Yaş həddi", "Возраст"],
  genre: ["Genre", "Janr", "Жанр"],
  address: ["Address", "Ünvan", "Адрес"],
  origin: ["From", "Haradan", "Откуда"],
  destination: ["To", "Haraya", "Куда"],
  query: ["Search", "Axtarış", "Поиск"],
  min_price: ["Min price", "Min qiymət", "Мин. цена"],
  max_price: ["Max price", "Maks qiymət", "Макс. цена"],
  sort: ["Sort", "Sıralama", "Порядок"],
  after: ["After", "Sonra", "После"],
  before: ["Before", "Əvvəl", "До"],
  max_stops: ["Max stops", "Maks dayanacaq", "Макс. пересадок"],
  brand: ["Brand", "Marka", "Бренд"],
  movie_id: ["Film", "Film", "Фильм"],
  cinema_id: ["Cinema", "Kinoteatr", "Кинотеатр"],
  in_stock: ["In stock", "Stokda", "В наличии"],
  min_rating: ["Min rating", "Min reytinq", "Мин. рейтинг"],
  descending: ["Descending", "Azalan", "По убыванию"],
};
const values = {
  one_way: ["One way", "Tək istiqamət", "В одну сторону"],
  round_trip: ["Round trip", "Gediş-dönüş", "Туда и обратно"],
  economy: ["Economy", "Ekonom", "Эконом"],
  business: ["Business", "Biznes", "Бизнес"],
  black: ["Black", "Qara", "Чёрный"],
  white: ["White", "Ağ", "Белый"],
  grey: ["Grey", "Boz", "Серый"],
  silver: ["Silver", "Gümüşü", "Серебристый"],
  blue: ["Blue", "Mavi", "Синий"],
  multicolor: ["Multicolour", "Rəngarəng", "Разноцветный"],
  English: ["English", "İngilis", "Английский"],
  Russian: ["Russian", "Rus", "Русский"],
  Azerbaijani: ["Azerbaijani", "Azərbaycan", "Азербайджанский"],
  audio: ["Audio", "Audio", "Аудио"],
  computers: ["Computers", "Kompüterlər", "Компьютеры"],
  phones: ["Phones", "Telefonlar", "Телефоны"],
  wearables: ["Wearables", "Geyilə bilən", "Носимые устройства"],
  sport: ["Sport", "İdman", "Спорт"],
  accessories: ["Accessories", "Aksesuarlar", "Аксессуары"],
  home: ["Home", "Ev", "Для дома"],
  gifts: ["Gifts", "Hədiyyələr", "Подарки"],
  "sci-fi": ["Sci-fi", "Fantastika", "Фантастика"],
  thriller: ["Thriller", "Triller", "Триллер"],
  comedy: ["Comedy", "Komediya", "Комедия"],
  drama: ["Drama", "Dram", "Драма"],
  action: ["Action", "Döyüş", "Боевик"],
  crime: ["Crime", "Cinayət", "Криминал"],
  horror: ["Horror", "Qorxu", "Ужасы"],
  mystery: ["Mystery", "Sirr", "Детектив"],
  animation: ["Animation", "Animasiya", "Мультфильм"],
  family: ["Family", "Ailə", "Семейный"],
  romance: ["Romance", "Romantika", "Романтика"],
  adventure: ["Adventure", "Macəra", "Приключения"],
};
const examples = {
  flights: [
    "Find a flight from Baku to Istanbul on Friday.",
    "Cümə günü Bakıdan İstanbula uçuş tap.",
    "Найди рейс из Баку в Стамбул в пятницу.",
  ],
  shopping: [
    "Find iPhone 17 Pro",
    "iPhone 17 Pro tap",
    "Найди iPhone 17 Pro",
  ],
  cinema: [
    "What is playing tonight?",
    "Bu axşam kinoda nə göstərilir?",
    "Что сегодня вечером идёт в кино?",
  ],
};
let lang = localStorage.getItem("superchat.language") || "en";
if (!["en", "az", "ru"].includes(lang)) lang = "en";
let session = null,
  sessions = [],
  config = null,
  busy = false,
  failed = null,
  pendingText = "",
  voiceWanted = false,
  recognition = null,
  voiceTimer = null,
  restartTimer = null,
  speaking = false;
const index = () => ({ en: 0, az: 1, ru: 2 })[lang];
const t = (k) => {
  if (["snapshot", "database"].includes(config?.data_mode)) k = snapshotLabels[k] || k;
  if (config?.data_mode === "database") k = ({snapshotMode: "databaseMode", snapshotCaption: "databaseCaption"})[k] || k;
  return (lex[k] || fieldNames[k] || [k, k, k])[index()];
};
const value = (v) =>
  v == null ? t("unknown") : typeof v === "boolean"
    ? v
      ? "✓"
      : "–"
    : values[v]
      ? values[v][index()]
      : String(v)
          .split(", ")
          .map((x) => (values[x] ? values[x][index()] : x))
          .join(", ");
const money = (n) =>
  n == null ? t("unknown") : new Intl.NumberFormat(
    lang === "az" ? "az-AZ" : lang === "ru" ? "ru-RU" : "en-US",
    { minimumFractionDigits: 2, maximumFractionDigits: 2 },
  ).format(n);
function applyLanguage() {
  document.documentElement.lang = lang;
  $("#language").value = lang;
  document.querySelectorAll("[data-t]").forEach((el) => {
    el.innerHTML = t(el.dataset.t);
  });
  $("#message-input").placeholder = t("input");
  $("#session-search").placeholder = t("search");
  $("#save-status").textContent = t(busy ? "saving" : "saved");
  localStorage.setItem("superchat.language", lang);
  if (config) {
    $("#reference-date").textContent = new Date(
      config.reference_date + "T12:00:00",
    ).toLocaleDateString(
      lang === "az" ? "az-AZ" : lang === "ru" ? "ru-RU" : "en-GB",
      { day: "numeric", month: "long", year: "numeric" },
    );
    $("#provider-info").textContent = t(
      config.ai_enabled ? "aiProvider" : "offlineProvider",
    );
  }
  renderSessions();
  if (session) {
    renderMessages();
    renderContext();
  }
  fillIcons();
}
async function api(path, options = {}) {
  const response = await fetch("/api" + path, {
    ...options,
    headers:
      options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json", ...options.headers },
  });
  if (!response.ok) {
    let message = t("networkError");
    try {
      const data = await response.json();
      if (typeof data.detail === "string") message = data.detail;
    } catch {}
    throw new Error(message);
  }
  return response.json();
}
function notice(message, retry = false) {
  $("#notice").hidden = !message;
  $("#notice").textContent = message || "";
  if (retry) {
    const b = document.createElement("button");
    b.textContent = t("retry");
    b.onclick = () => failed && send(failed.text, failed.id, failed.language);
    $("#notice").append(b);
  }
}
function setBusy(v) {
  busy = v;
  $("#send-button").disabled = v;
  $("#image-button").disabled = v;
  $("#new-chat").disabled = v;
  $("#continue-button").disabled = v;
  $("#save-status").textContent = t(v ? "saving" : "saved");
  document
    .querySelectorAll(".session-item,.session-delete,.card-action,.suggestion")
    .forEach((el) => (el.disabled = v || el.dataset.unavailable === "true"));
}
function scrollBottom() {
  $("#chat-scroll").scrollTop = $("#chat-scroll").scrollHeight;
}
function closeMobile() {
  $("#sidebar").classList.remove("open");
  $("#backdrop").hidden = true;
}
function renderSessions() {
  const q = $("#session-search").value.toLowerCase();
  $("#session-count").textContent = sessions.length;
  $("#session-list").innerHTML =
    sessions
      .filter((s) => s.title.toLowerCase().includes(q))
      .map(
        (s) =>
          `<div class="session-row"><button class="session-item ${session?.id === s.id ? "active" : ""}" data-session="${esc(s.id)}" title="${esc(s.title)}" ${busy ? "disabled" : ""}>${icon("chat")}<span>${esc(s.title === "New conversation" ? t("newTitle") : s.title)}</span></button><button class="session-delete" data-delete-session="${esc(s.id)}" title="${esc(t("deleteChat"))}" aria-label="${esc(t("deleteChat") + ': ' + s.title)}" ${busy ? "disabled" : ""}>${icon("trash")}</button></div>`,
      )
      .join("") || `<p class="empty-sessions">${esc(t("noChats"))}</p>`;
}
async function refreshSessions() {
  sessions = await api("/sessions");
  renderSessions();
}
function confirmChatDeletion(title) {
  const dialog = $("#delete-dialog");
  if (dialog.open) return Promise.resolve(false);
  $("#delete-heading").textContent = t("deleteHeading");
  $("#delete-description").textContent = t("deleteDescription");
  $("#delete-chat-title").textContent = title;
  $("#delete-warning").textContent = t("deleteWarning");
  $("#delete-cancel").textContent = t("keepChat");
  $("#delete-confirm").textContent = t("deleteChat");
  dialog.returnValue = "";
  return new Promise(resolve => {
    dialog.onclose = () => {
      dialog.onclose = null;
      resolve(dialog.returnValue === "delete");
    };
    dialog.showModal();
    $("#delete-cancel").focus();
  });
}
async function deleteSession(id) {
  if (busy) return;
  const target = sessions.find(s => s.id === id);
  if (!target || !await confirmChatDeletion(target.title === "New conversation" ? t("newTitle") : target.title)) return;
  if (busy || !sessions.some(s => s.id === id)) return;
  const active = session?.id === id;
  if (active) stopVoice();
  setBusy(true);
  notice("");
  try {
    await api("/sessions/" + id, {method: "DELETE"});
    sessions = sessions.filter(s => s.id !== id);
    if (active) {
      session = null;
      localStorage.removeItem("superchat.session");
      failed = null;
      pendingText = "";
      $("#message-input").value = "";
      renderMessages();
      renderContext();
    }
    renderSessions();
    if (active && sessions.length) {
      session = await api("/sessions/" + sessions[0].id);
      localStorage.setItem("superchat.session", session.id);
      applyLanguage();
      scrollBottom();
    }
  } catch (error) {
    notice(error.message);
  } finally {
    setBusy(false);
    renderSessions();
    renderContext();
  }
}
async function loadSession(id) {
  if (busy) return;
  stopVoice();
  notice("");
  session = await api("/sessions/" + id);
  localStorage.setItem("superchat.session", id);
  // The selector is a browser preference, not a detected message language.
  applyLanguage();
  closeMobile();
  scrollBottom();
}
async function newSession(source = false) {
  if (busy) return;
  stopVoice();
  notice("");
  session = await api("/sessions", {
    method: "POST",
    body: JSON.stringify({
      language: lang,
      source_id: source ? session?.id : null,
    }),
  });
  localStorage.setItem("superchat.session", session.id);
  await refreshSessions();
  renderMessages();
  renderContext();
  closeMobile();
  $("#message-input").focus();
}
const domainIcon = (d) =>
  ({ flights: "plane", shopping: "bag", cinema: "film" })[d] || "sparkle";
function actionText(kind, id, snapshot = false) {
  if (kind === "shopping")
    return [
      `Add ${id} to my cart`,
      `Səbətə ${id} əlavə et`,
      `Добавь ${id} в корзину`,
    ][index()];
  if (snapshot) return [`Save ${id} to my plans`, `${id} planlarda saxla`, `Сохрани ${id} в планах`][index()];
  return [
    `Reserve one seat for ${id}`,
    `${id} üçün bir yer bron et`,
    `Забронируй одно место ${id}`,
  ][index()];
}
function availabilityText(c) {
  if (c.snapshot) return t(c.availability === "listed_in_stock" ? "listedStock" : c.availability === "out_of_stock" ? "soldOut" : "unknownAvailability");
  return c.available == null ? t("unknownAvailability") : c.available > 0 ? `${c.available} ${t("available")}` : t("soldOut");
}
function safeSource(url) {
  try { const parsed = new URL(url); return ["https:", "http:"].includes(parsed.protocol) && !parsed.username && !parsed.password ? parsed.href : null; }
  catch { return null; }
}
function cardHTML(c) {
  const link = safeSource(c.source_url);
  const unavailable = c.available === 0 || c.availability === "out_of_stock";
  const button = c.snapshot && c.action === "source" ? "" : `<button class="card-action" data-unavailable="${unavailable}" data-prompt="${esc(actionText(c.kind, c.id, c.snapshot))}" ${unavailable || busy ? "disabled" : ""}>${esc(t(c.snapshot ? (c.kind === "shopping" ? "listAdd" : "savePlan") : c.kind === "shopping" ? "add" : "reserve"))}</button>`;
  const warnings = [c.price_conflict && "conflict", c.stale && "stale", c.expired && "expired", c.nearby_airport_search && "nearby", c.provider_cached && "cachedFare"].filter(Boolean);
  return `<article class="result-card"><div class="result-card-top"><span class="result-symbol ${esc(c.kind)}">${icon(domainIcon(c.kind))}</span><span class="result-id">${esc(c.id)}</span><span class="result-availability ${unavailable ? "sold-out" : ""}">${esc(availabilityText(c))}</span></div>${c.image_url?.startsWith("/api/catalogue/images/") ? `<img class="catalogue-image" src="${esc(c.image_url)}" alt="${esc(c.title)}" loading="lazy">` : ""}<h3>${esc(c.title)}</h3>${c.similarity != null ? `<p class="similarity-score">${esc(t("similarity"))}: ${Number(c.similarity).toFixed(2)}</p>` : ""}${c.content_language && c.content_language !== lang ? `<small class="source-details">${esc(t("sourceText"))}: ${esc(t(c.content_language))}</small>` : ""}<p class="result-subtitle">${esc(c.subtitle)}</p>${warnings.map(k => `<p class="snapshot-warning">${esc(t(k))}</p>`).join("")}<dl class="result-fields">${c.fields.map(f => `<div class="${["description", "address"].includes(f.label) ? "wide-field" : ""}"><dt>${esc(t(f.label))}</dt><dd>${esc(value(f.value))}</dd></div>`).join("")}</dl><div class="result-bottom"><span class="result-price">${money(c.price)} <small>${c.price == null ? "" : "AZN"}${c.quantity ? ` × ${c.quantity}` : ""}</small>${c.snapshot ? `<small>${esc(t(c.price_scope === "entire_round_trip" ? "returnPrice" : "snapshotPrice"))}</small>` : ""}</span>${button}</div>${link ? `<a class="source-link" href="${esc(link)}" target="_blank" rel="noopener noreferrer">${esc(t(config?.data_mode === "database" ? ({shopping: "birmarketOpen", cinema: "cinemaOpen", flights: "flightOpen"})[c.kind] : "sourceOpen"))} ↗</a>` : ""}<details class="source-details"><summary>${esc(t("source"))}</summary><p>${esc(c.source)}${c.source_title ? `<br>${esc(c.source_title)}` : ""}<br>ID: ${esc(c.id)}${c.fetched_at ? `<br>${esc(t("collected"))}: ${esc(c.fetched_at)}` : ""}${(c.price_observations || []).map(o => `<br>${esc(o.price_azn)} AZN · ${esc(o.source_url)}`).join("")}</p></details></article>`;
}
function comparisonHTML(cards) {
  return `<div class="comparison-wrap"><table><caption class="sr-only">${esc(t("comparison"))}</caption><thead><tr><th>${esc(t("item"))}</th><th>${esc(t("price"))}</th><th>${esc(t("available"))}</th>${cards[0]?.kind === "flights" ? `<th>${esc(t("stops"))}</th><th>${esc(t("baggage"))}</th>` : ""}</tr></thead><tbody>${cards.map((c) => `<tr><td>${esc(c.title)} · ${esc(c.id)}</td><td>${money(c.price)} AZN</td><td>${esc(availabilityText(c))}</td>${c.kind === "flights" ? `<td>${esc(value(c.fields.find((f) => f.label === "stops")?.value))}</td><td>${esc(value(c.fields.find((f) => f.label === "baggage")?.value))}</td>` : ""}</tr>`).join("")}</tbody></table></div>`;
}
function savedPlanHTML(r, removable = false) {
  const link = safeSource(r.source_url);
  const remove = [`Unsave ${r.item_id}`, `Saxlanılmış planı sil ${r.item_id}`, `Удали сохранённый план ${r.item_id}`][index()];
  return `<div class="context-item">${removable ? `<button data-prompt="${esc(remove)}" aria-label="${esc(t("removePlan"))}">×</button>` : ""}<strong>${esc(r.title || r.item_id)}</strong><br>${esc(r.subtitle || "")}<br><small>${esc(t("localPlan"))}</small><br>${r.quantity} × ${money(r.unit_price)} AZN${link ? `<br><a class="source-link" href="${esc(link)}" target="_blank" rel="noopener noreferrer">${esc(t("sourceOpen"))} ↗</a>` : ""}</div>`;
}
function replyHTML(m) {
  return `<article class="message assistant"><div class="assistant-head"><span class="brand-mark">B</span><span>Bir SuperChat</span>${(m.route?.domains || []).map((d) => `<span class="domain-badge ${esc(d)}">${esc(t(d))}</span>`).join("")}<small>${esc(t("grounded"))}</small></div>${m.text ? `<p class="message-text">${esc(m.text)}</p>` : ""}${(
    m.sections || []
  )
    .map(
      (s) =>
        `<section class="response-section"><div class="section-heading">${icon(domainIcon(s.domain))}<span>${esc(t(s.domain))}</span></div><p class="message-text">${esc(s.text)}</p>${s.total_matches > s.cards.length ? `<p class="source-details">${esc(t("shown"))} ${s.cards.length} ${esc(t("of"))} ${s.total_matches}. ${esc(t("refine"))}</p>` : ""}${
          s.filters
            ? `<div class="filters">${Object.entries(s.filters)
                .map(
                  ([k, v]) =>
                    `<span class="filter-chip">${esc(t(k))}: ${esc(value(v))}</span>`,
                )
                .join("")}</div>`
            : ""
        }${s.comparison ? comparisonHTML(s.cards) : ""}<div class="result-grid">${s.cards.map(cardHTML).join("")}</div>${s.has_more ? `<button class="card-action" data-prompt="${esc(`Show more ${s.domain}`)}" ${busy ? "disabled" : ""}>${esc(t("showMore"))}</button>` : ""}${(s.reservations || []).map((r) => r.status === "saved_local" ? savedPlanHTML(r) : `<div class="confirmation">${icon("check")} <strong>${esc(r.code)}</strong> · ${esc(r.item_id)} · ${r.quantity} × ${money(r.unit_price)} = ${money(r.total)} AZN</div>`).join("")}</section>`,
    )
    .join(
      "",
    )}${m.notice ? `<p class="source-details">${esc(t(m.notice === "ai_auth_failed" ? "authFailed" : "fallback"))}</p>` : ""}</article>`;
}
function renderMessages() {
  if (!session) {
    $("#welcome").hidden = false;
    $("#messages").innerHTML = "";
    $("#context-return").hidden = true;
    return;
  }
  $("#welcome").hidden = session.messages.length > 0;
  $("#messages").innerHTML = session.messages
    .map((m) =>
      m.role === "user"
        ? `<article class="message user"><div class="user-bubble">${m.attachment ? icon("image") : ""}${esc(m.text)}</div></article>`
        : replyHTML(m),
    )
    .join("");
  if (session.source) {
    $("#context-return").hidden = false;
    $("#context-return").textContent =
      t("inherited") + " " + session.source.title;
  } else $("#context-return").hidden = true;
}
function findCard(id) {
  for (const m of [...session.messages].reverse())
    for (const s of m.sections || [])
      for (const c of s.cards || []) if (c.id === id) return c;
  return null;
}
function renderContext() {
  const state = session?.state || {cart: {}, reservations: [], domains: {}};
  let total = 0;
  $("#cart-count").textContent = Object.values(state.cart).reduce(
    (a, b) => a + b,
    0,
  );
  $("#cart-content").innerHTML = Object.keys(state.cart).length
    ? Object.entries(state.cart)
        .map(([id, qty]) => {
          const c = findCard(id);
          if (total !== null) total = c?.price == null ? null : total + c.price * qty;
          return `<div class="context-item"><button data-prompt="${esc([`Remove ${qty} items of ${id} from cart`, `${id} məhsulundan ${qty} ədəd səbətdən sil`, `Удали ${qty} штук ${id} из корзины`][index()])}" aria-label="${esc("Remove " + id)}">×</button><strong>${esc(c?.title || id)}</strong><br>${qty} × ${c ? money(c.price) : "—"} AZN</div>`;
        })
        .join("") +
      `<div class="context-total"><span>${esc(t("total"))}</span><strong>${money(total)} AZN</strong></div>`
    : `<div class="context-empty">${icon("bag")}<p>${esc(t("cartEmpty"))}</p><small>${esc(t("cartHint"))}</small></div>`;
  $("#booking-count").textContent = state.reservations.length;
  $("#bookings-content").innerHTML = state.reservations.length
    ? state.reservations
        .map(
          (r) =>
            r.status === "saved_local" ? savedPlanHTML(r, true) : `<div class="context-item"><strong>${esc(r.code)}</strong><br>${esc(r.item_id)} · ${r.quantity} × ${money(r.unit_price)} AZN<br>${esc(t("total"))}: ${money(r.total)} AZN</div>`,
        )
        .join("")
    : `<div class="context-empty">${icon("ticket")}<p>${esc(t("bookingEmpty"))}</p><small>${esc(t("bookingHint"))}</small></div>`;
  const active = Object.entries(state.domains).filter(
    ([_, d]) => d.results.length || Object.keys(d.filters).length,
  );
  $("#memory-content").innerHTML = active.length
    ? active
        .map(
          ([d, s]) =>
            `<div class="memory-domain">${icon(domainIcon(d))}<button data-prompt="${esc([`Back to ${d}`, `${d === "flights" ? "uçuşlara" : d === "shopping" ? "məhsullara" : "kinoya"} qayıt`, `Вернёмся к ${d === "flights" ? "рейсам" : d === "shopping" ? "товарам" : "кино"}`][index()])}">${esc(t(d))}</button><small>${s.results.length}</small></div>`,
        )
        .join("")
    : `<p>${esc(t("memoryEmpty"))}</p>`;
  $("#continue-button").disabled = busy || !active.length;
}
async function send(text = null, id = null, replyLanguage = lang) {
  if (busy) return;
  text = (text ?? $("#message-input").value).trim();
  if (!text) return;
  if (!session) await newSession();
  const target = session.id;
  const requestId = id || crypto.randomUUID();
  failed = null;
  notice("");
  setBusy(true);
  $("#message-input").value = "";
  pendingText = "";
  renderMessages();
  $("#welcome").hidden = true;
  $("#messages").insertAdjacentHTML(
    "beforeend",
    `<article class="message user"><div class="user-bubble">${esc(text)}</div></article><div class="thinking" id="thinking"><i></i><i></i><i></i><span>${esc(t("thinking"))}</span></div>`,
  );
  scrollBottom();
  try {
    const data = await api(`/sessions/${target}/messages`, {
      method: "POST",
      body: JSON.stringify({ text, request_id: requestId, language: replyLanguage }),
    });
    session = data.session;
    applyLanguage();
    await refreshSessions();
    if ($("#read-aloud").checked) readReply(data.reply);
  } catch (error) {
    failed = { text, id: requestId, language: replyLanguage };
    $("#message-input").value = text;
    notice(error.message, true);
  } finally {
    setBusy(false);
    $("#thinking")?.remove();
    renderContext();
    scrollBottom();
  }
}
async function upload(file) {
  if (busy || !file) return;
  if (
    file.size > 8 * 1024 * 1024 ||
    !["image/jpeg", "image/png", "image/webp"].includes(file.type)
  ) {
    notice(t("photoError"));
    return;
  }
  setBusy(true);
  notice("");
  $("#welcome").hidden = true;
  $("#messages").insertAdjacentHTML(
    "beforeend",
    `<div id="thinking" class="thinking"><i></i><i></i><i></i><span>${esc(t("imageThinking"))}</span></div>`,
  );
  scrollBottom();
  try {
    const form = new FormData();
    form.append("file", file);
    form.append("request_id", crypto.randomUUID());
    form.append("language", lang);
    const data = await api(`/sessions/${session.id}/images`, {
      method: "POST",
      body: form,
    });
    session = data.session;
    renderMessages();
    renderContext();
    await refreshSessions();
  } catch (e) {
    notice(e.message);
  } finally {
    setBusy(false);
    $("#thinking")?.remove();
    $("#image-input").value = "";
    scrollBottom();
  }
}
function stopVoice() {
  voiceWanted = false;
  clearTimeout(voiceTimer);
  clearTimeout(restartTimer);
  recognition?.abort();
  $("#voice-button").classList.remove("is-listening");
  $("#voice-button").setAttribute("aria-pressed", "false");
  $("#voice-status").classList.remove("active");
  $("#voice-status").textContent = t("voiceHint");
}
function startRecognition() {
  if (!voiceWanted || speaking) return;
  try {
    recognition.lang = { en: "en-US", az: "az-AZ", ru: "ru-RU" }[lang];
    recognition.start();
  } catch {}
}
function voice() {
  if (voiceWanted) {
    stopVoice();
    return;
  }
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    notice(t("voiceUnavailable"));
    return;
  }
  notice("");
  voiceWanted = true;
  recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.onstart = () => {
    $("#voice-status").textContent = t("listening");
    $("#voice-button").classList.add("is-listening");
    $("#voice-button").setAttribute("aria-pressed", "true");
    $("#voice-status").classList.add("active");
  };
  recognition.onspeechstart = () => {
    $("#voice-status").textContent = t("hearing");
    clearTimeout(voiceTimer);
  };
  recognition.onresult = (event) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      if (event.results[i].isFinal)
        pendingText += " " + event.results[i][0].transcript;
      else interim += event.results[i][0].transcript;
    }
    $("#message-input").value = (pendingText + " " + interim).trim();
    clearTimeout(voiceTimer);
    if (pendingText.trim()) voiceTimer = setTimeout(flushVoice, 1200);
  };
  recognition.onspeechend = () => {
    clearTimeout(voiceTimer);
    voiceTimer = setTimeout(flushVoice, 1200);
  };
  recognition.onerror = (e) => {
    if (
      ["not-allowed", "audio-capture", "service-not-allowed"].includes(e.error)
    ) {
      stopVoice();
      notice(t("voiceDenied"));
    } else if (e.error === "network") {
      stopVoice();
      notice(t("voiceNetwork"));
    }
  };
  recognition.onend = () => {
    if (voiceWanted && !speaking)
      restartTimer = setTimeout(startRecognition, 500);
  };
  startRecognition();
}
function flushVoice() {
  if (!voiceWanted || !pendingText.trim()) return;
  if (busy) {
    voiceTimer = setTimeout(flushVoice, 1000);
    return;
  }
  const text = pendingText.trim();
  pendingText = "";
  send(text);
}
function readReply(reply) {
  if (!("speechSynthesis" in window)) return;
  speaking = true;
  recognition?.abort();
  const speech = new SpeechSynthesisUtterance(
    [reply.text, ...reply.sections.map((s) => s.text)]
      .filter(Boolean)
      .join(" "),
  );
  speech.lang = { en: "en-US", az: "az-AZ", ru: "ru-RU" }[reply.language];
  const done = () => {
    speaking = false;
    if (voiceWanted) startRecognition();
  };
  speech.onend = done;
  speech.onerror = done;
  window.speechSynthesis.speak(speech);
}
$("#composer").addEventListener("submit", (e) => {
  e.preventDefault();
  send();
});
$("#message-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault();
    send();
  }
});
$("#new-chat").onclick = () => newSession().catch((e) => notice(e.message));
$("#continue-button").onclick = () =>
  newSession(true).catch((e) => notice(e.message));
$("#session-search").oninput = renderSessions;
document.addEventListener("click", (e) => {
  const deleteButton = e.target.closest("[data-delete-session]");
  if (deleteButton) {
    deleteSession(deleteButton.dataset.deleteSession);
    return;
  }
  const sessionButton = e.target.closest("[data-session]");
  if (sessionButton)
    loadSession(sessionButton.dataset.session).catch((err) =>
      notice(err.message),
    );
  const prompt = e.target.closest("[data-prompt]");
  if (prompt) send(prompt.dataset.prompt);
  const example = e.target.closest("[data-example]");
  if (example) send(examples[example.dataset.example][index()]);
});
$("#language").onchange = () => {
  lang = $("#language").value;
  stopVoice();
  applyLanguage();
};
$("#image-button").onclick = () => $("#image-input").click();
$("#image-input").onchange = (e) => upload(e.target.files[0]);
$("#voice-button").onclick = voice;
$("#export-button").onclick = () => {
  if (session) window.location.assign(`/api/sessions/${session.id}/export`);
};
$("#about-button").onclick = () => $("#about-dialog").showModal();
$("#close-about").onclick = () => $("#about-dialog").close();
$("#delete-cancel").onclick = () => $("#delete-dialog").close("cancel");
$("#delete-confirm").onclick = () => $("#delete-dialog").close("delete");
$("#delete-dialog").onclick = e => {
  if (e.target === $("#delete-dialog")) $("#delete-dialog").close("cancel");
};
$("#about-dialog").onclick = (e) => {
  if (e.target === $("#about-dialog")) $("#about-dialog").close();
};
$("#context-toggle").onclick = () =>
  $("#context-panel").classList.toggle("open");
$("#menu-button").onclick = () => {
  $("#sidebar").classList.toggle("open");
  $("#backdrop").hidden = !$("#sidebar").classList.contains("open");
};
$("#backdrop").onclick = closeMobile;
document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === "k") {
    e.preventDefault();
    if ($("#delete-dialog").open) return;
    newSession().catch((err) => notice(err.message));
  }
  if (e.key === "Escape") {
    closeMobile();
    $("#context-panel").classList.remove("open");
  }
});
window.addEventListener("beforeunload", stopVoice);
async function init() {
  fillIcons();
  applyLanguage();
  try {
    [config, sessions] = await Promise.all([api("/config"), api("/sessions")]);
    const saved = localStorage.getItem("superchat.session");
    if (saved && sessions.some((s) => s.id === saved)) await loadSession(saved);
    else if (sessions.length) await loadSession(sessions[0].id);
    else await newSession();
    applyLanguage();
  } catch (e) {
    notice(e.message);
  }
}
init();

"use strict";
const $ = (s) => document.querySelector(s);
const icons = {
  plus: "M12 5v14M5 12h14",
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
    "Wireless headphones<br>under 100 AZN",
    "100 AZN-dən ucuz<br>simsiz qulaqlıq",
    "Беспроводные наушники<br>до 100 AZN",
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
    "Could not reach SuperChat. Your message is kept — try again.",
    "SuperChat-a qoşulmaq olmadı. Mesajınız saxlanılıb — yenidən sınayın.",
    "Не удалось связаться с SuperChat. Сообщение сохранено — повторите попытку.",
  ],
  fallback: [
    "AI is unavailable. This reply used the offline assistant.",
    "AI əlçatan deyil. Bu cavab oflayn köməkçi ilə hazırlandı.",
    "ИИ недоступен. Ответ подготовлен офлайн-помощником.",
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
    "Offline assistant active. Add your OpenRouter key to .env and restart to enable AI understanding.",
    "Oflayn köməkçi aktivdir. AI üçün .env faylına OpenRouter açarı əlavə edib yenidən başladın.",
    "Работает офлайн-помощник. Для ИИ добавьте ключ OpenRouter в .env и перезапустите.",
  ],
  aiProvider: [
    "OpenRouter is connected. Catalogue facts are still verified locally.",
    "OpenRouter qoşulub. Kataloq məlumatları yenə yerli yoxlanılır.",
    "OpenRouter подключён. Данные каталога проверяются локально.",
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
const fieldNames = {
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
    "Do you have wireless headphones under 100 AZN?",
    "100 manatdan ucuz simsiz qulaqlıq var?",
    "Есть беспроводные наушники до 100 AZN?",
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
const t = (k) => (lex[k] || fieldNames[k] || [k, k, k])[index()];
const value = (v) =>
  typeof v === "boolean"
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
  new Intl.NumberFormat(
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
    b.onclick = () => failed && send(failed.text, failed.id);
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
    .querySelectorAll(".session-item,.card-action,.suggestion")
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
          `<button class="session-item ${session?.id === s.id ? "active" : ""}" data-session="${esc(s.id)}" title="${esc(s.title)}" ${busy ? "disabled" : ""}>${icon("chat")}<span>${esc(s.title === "New conversation" ? t("newTitle") : s.title)}</span></button>`,
      )
      .join("") || `<p class="empty-sessions">${esc(t("noChats"))}</p>`;
}
async function refreshSessions() {
  sessions = await api("/sessions");
  renderSessions();
}
async function loadSession(id) {
  if (busy) return;
  stopVoice();
  notice("");
  session = await api("/sessions/" + id);
  localStorage.setItem("superchat.session", id);
  lang = session.state.language;
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
function actionText(kind, id) {
  if (kind === "shopping")
    return [
      `Add ${id} to my cart`,
      `Səbətə ${id} əlavə et`,
      `Добавь ${id} в корзину`,
    ][index()];
  return [
    `Reserve one seat for ${id}`,
    `${id} üçün bir yer bron et`,
    `Забронируй одно место ${id}`,
  ][index()];
}
function cardHTML(c) {
  return `<article class="result-card"><div class="result-card-top"><span class="result-symbol ${esc(c.kind)}">${icon(domainIcon(c.kind))}</span><span class="result-id">${esc(c.id)}</span><span class="result-availability ${c.available === 0 ? "sold-out" : ""}">${c.available > 0 ? `${c.available} ${esc(t("available"))}` : esc(t("soldOut"))}</span></div><h3>${esc(c.title)}</h3><p class="result-subtitle">${esc(c.subtitle)}</p><dl class="result-fields">${c.fields.map((f) => `<div class="${["description", "address"].includes(f.label) ? "wide-field" : ""}"><dt>${esc(t(f.label))}</dt><dd>${esc(value(f.value))}</dd></div>`).join("")}</dl><div class="result-bottom"><span class="result-price">${money(c.price)} <small>AZN${c.quantity ? ` × ${c.quantity}` : ""}</small></span><button class="card-action" data-unavailable="${c.available === 0}" data-prompt="${esc(actionText(c.kind, c.id))}" ${c.available === 0 || busy ? "disabled" : ""}>${esc(t(c.kind === "shopping" ? "add" : "reserve"))}</button></div><details class="source-details"><summary>${esc(t("source"))}</summary><p>${esc(c.source)}<br>ID: ${esc(c.id)}</p></details></article>`;
}
function comparisonHTML(cards) {
  return `<div class="comparison-wrap"><table><caption class="sr-only">${esc(t("comparison"))}</caption><thead><tr><th>${esc(t("item"))}</th><th>${esc(t("price"))}</th><th>${esc(t("available"))}</th>${cards[0]?.kind === "flights" ? `<th>${esc(t("stops"))}</th><th>${esc(t("baggage"))}</th>` : ""}</tr></thead><tbody>${cards.map((c) => `<tr><td>${esc(c.title)} · ${esc(c.id)}</td><td>${money(c.price)} AZN</td><td>${c.available}</td>${c.kind === "flights" ? `<td>${c.fields.find((f) => f.label === "stops")?.value}</td><td>${c.fields.find((f) => f.label === "baggage")?.value} kg</td>` : ""}</tr>`).join("")}</tbody></table></div>`;
}
function replyHTML(m) {
  return `<article class="message assistant"><div class="assistant-head"><span class="brand-mark">s</span><span>SuperChat</span>${(m.route?.domains || []).map((d) => `<span class="domain-badge ${esc(d)}">${esc(t(d))}</span>`).join("")}<small>${esc(t("grounded"))}</small></div>${m.text ? `<p class="message-text">${esc(m.text)}</p>` : ""}${(
    m.sections || []
  )
    .map(
      (s) =>
        `<section class="response-section"><div class="section-heading">${icon(domainIcon(s.domain))}<span>${esc(t(s.domain))}</span></div><p class="message-text">${esc(s.text)}</p>${
          s.filters
            ? `<div class="filters">${Object.entries(s.filters)
                .map(
                  ([k, v]) =>
                    `<span class="filter-chip">${esc(t(k))}: ${esc(value(v))}</span>`,
                )
                .join("")}</div>`
            : ""
        }${s.comparison ? comparisonHTML(s.cards) : ""}<div class="result-grid">${s.cards.map(cardHTML).join("")}</div>${(s.reservations || []).map((r) => `<div class="confirmation">${icon("check")} <strong>${esc(r.code)}</strong> · ${esc(r.item_id)} · ${r.quantity} × ${money(r.unit_price)} = ${money(r.total)} AZN</div>`).join("")}</section>`,
    )
    .join(
      "",
    )}${m.notice ? `<p class="source-details">${esc(t("fallback"))}</p>` : ""}</article>`;
}
function renderMessages() {
  if (!session) return;
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
  if (!session) return;
  const state = session.state;
  let total = 0;
  $("#cart-count").textContent = Object.values(state.cart).reduce(
    (a, b) => a + b,
    0,
  );
  $("#cart-content").innerHTML = Object.keys(state.cart).length
    ? Object.entries(state.cart)
        .map(([id, qty]) => {
          const c = findCard(id);
          total += (c?.price || 0) * qty;
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
            `<div class="context-item"><strong>${esc(r.code)}</strong><br>${esc(r.item_id)} · ${r.quantity} × ${money(r.unit_price)} AZN<br>${esc(t("total"))}: ${money(r.total)} AZN</div>`,
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
async function send(text = null, id = null) {
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
      body: JSON.stringify({ text, request_id: requestId }),
    });
    session = data.session;
    lang = session.state.language;
    applyLanguage();
    await refreshSessions();
    if ($("#read-aloud").checked) readReply(data.reply);
  } catch (error) {
    failed = { text, id: requestId };
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

# Routing test log

Date: 2 November 2026. Offline rule router; reference date 2026-11-02.

**102/106 correct (96.2%).**

Author-written regression set, including the brief, translated equivalents, context-dependent follow-ups, mixed-language requests and four harder paraphrases. This is not an independent benchmark or a general accuracy guarantee. No OpenRouter key was supplied, so hosted-model accuracy is not measured.

| Language | Correct | Total | Accuracy |
|---|---:|---:|---:|
| en | 33 | 35 | 94.3% |
| az | 33 | 34 | 97.1% |
| ru | 33 | 34 | 97.1% |
| mixed | 3 | 3 | 100.0% |

## Error analysis

- `Looking for cans for my commute`: expected shopping, got ambiguous.
- `I want to catch a flick`: expected cinema, got ambiguous.
- `Мне нужен перелёт в Париж`: expected flights, got ambiguous.
- `Mənə qulaq üçün yaxşı bir cihaz lazımdır`: expected shopping, got ambiguous.

Rules recognize catalogue terms and explicit follow-ups. Unseen slang and indirect descriptions can become clarifications rather than domain matches. Optional OpenRouter parsing targets those cases; it is not counted in these results. No routing error permits invented catalogue records.

## Complete results

| # | Language | Expected | Actual | Pass | Input |
|---:|---|---|---|---|---|
| 1 | en | flights | flights | yes | Find flights from Baku to Istanbul on Friday |
| 2 | en | flights | flights | yes | Flights to Dubai tomorrow |
| 3 | en | flights | flights | yes | Show direct flights to Moscow |
| 4 | en | flights | flights | yes | How much baggage on F001? |
| 5 | en | flights | flights | yes | Compare F001 and F002 |
| 6 | en | flights | flights | yes | Reserve F003 |
| 7 | en | flights | flights | yes | Caspian Air flights on Saturday |
| 8 | en | flights | flights | yes | Find me business class flights |
| 9 | en | shopping | shopping | yes | Show me laptops |
| 10 | en | shopping | shopping | yes | Wireless headphones under 100 AZN |
| 11 | en | shopping | shopping | yes | Add P010 to my cart |
| 12 | en | shopping | shopping | yes | Remove P001 from the cart |
| 13 | en | shopping | shopping | yes | Show products from Sonivo |
| 14 | en | shopping | shopping | yes | Compare P003 and P004 |
| 15 | en | shopping | shopping | yes | Do you have black running shoes? |
| 16 | en | shopping | shopping | yes | Find a gift under 50 AZN |
| 17 | en | cinema | cinema | yes | What is playing tonight? |
| 18 | en | cinema | cinema | yes | English sci-fi films this Saturday |
| 19 | en | cinema | cinema | yes | Any seats for Orbit Zero? |
| 20 | en | cinema | cinema | yes | Reserve two tickets for S001 |
| 21 | en | cinema | cinema | yes | Showtimes at CinemaPlus 28 Mall |
| 22 | en | cinema | cinema | yes | Films rated above 8 |
| 23 | en | mixed | mixed | yes | Flights to Istanbul and a backpack for my trip |
| 24 | en | mixed | mixed | yes | Headphones and cinema tickets |
| 25 | en | mixed | mixed | yes | A flight, a laptop and a movie |
| 26 | en | ambiguous | ambiguous | yes | Show me something good |
| 27 | en | ambiguous | ambiguous | yes | Book two seats |
| 28 | en | out_of_scope | out_of_scope | yes | What is the weather in Ganja? |
| 29 | en | out_of_scope | out_of_scope | yes | Write Python code |
| 30 | en | follow_up | follow_up | yes | The cheaper one |
| 31 | en | follow_up | follow_up | yes | And for Saturday? |
| 32 | en | follow_up | follow_up | yes | The second one |
| 33 | en | ambiguous | ambiguous | yes | Book it |
| 34 | az | flights | flights | yes | Cümə günü Bakıdan İstanbula uçuş tap |
| 35 | az | flights | flights | yes | Sabah Dubaya uçuş var? |
| 36 | az | flights | flights | yes | Moskvaya birbaşa uçuş göstər |
| 37 | az | flights | flights | yes | F001 baqaj limiti nədir? |
| 38 | az | flights | flights | yes | F001 və F002 müqayisə et |
| 39 | az | flights | flights | yes | F003 bron et |
| 40 | az | flights | flights | yes | Şənbə günü təyyarə bileti |
| 41 | az | flights | flights | yes | Uçuşları qiymətə görə sırala |
| 42 | az | shopping | shopping | yes | Noutbukları göstər |
| 43 | az | shopping | shopping | yes | 100 manatdan ucuz simsiz qulaqlıq |
| 44 | az | shopping | shopping | yes | P010 səbətə əlavə et |
| 45 | az | shopping | shopping | yes | P001 səbətdən sil |
| 46 | az | shopping | shopping | yes | Sonivo məhsullarını göstər |
| 47 | az | shopping | shopping | yes | P003 və P004 müqayisə et |
| 48 | az | shopping | shopping | yes | Qara qaçış ayaqqabısı var? |
| 49 | az | shopping | shopping | yes | 50 manatdan ucuz hədiyyə tap |
| 50 | az | cinema | cinema | yes | Bu axşam kinoda nə var? |
| 51 | az | cinema | cinema | yes | Şənbə üçün fantastik film |
| 52 | az | cinema | cinema | yes | Orbit Zero üçün yer var? |
| 53 | az | cinema | cinema | yes | S001 üçün iki bilet bron et |
| 54 | az | cinema | cinema | yes | CinemaPlus 28 Mall seansları |
| 55 | az | cinema | cinema | yes | Reytinqi 8-dən yuxarı filmlər |
| 56 | az | mixed | mixed | yes | İstanbula uçuş və səfər üçün çanta |
| 57 | az | mixed | mixed | yes | Qulaqlıq və kino bileti |
| 58 | az | mixed | mixed | yes | Uçuş, noutbuk və film |
| 59 | az | ambiguous | ambiguous | yes | Mənə yaxşı bir şey göstər |
| 60 | az | ambiguous | ambiguous | yes | İki yer bron et |
| 61 | az | out_of_scope | out_of_scope | yes | Gəncədə hava necədir? |
| 62 | az | out_of_scope | out_of_scope | yes | Python kodu yaz |
| 63 | az | follow_up | follow_up | yes | Ucuz olanı |
| 64 | az | follow_up | follow_up | yes | Bəs şənbə günü? |
| 65 | az | follow_up | follow_up | yes | İkinci olanı |
| 66 | az | ambiguous | ambiguous | yes | Onu bron et |
| 67 | ru | flights | flights | yes | Найди рейс из Баку в Стамбул в пятницу |
| 68 | ru | flights | flights | yes | Рейсы в Дубай завтра |
| 69 | ru | flights | flights | yes | Прямые рейсы в Москву |
| 70 | ru | flights | flights | yes | Какой багаж на F001? |
| 71 | ru | flights | flights | yes | Сравни F001 и F002 |
| 72 | ru | flights | flights | yes | Забронируй F003 |
| 73 | ru | flights | flights | yes | Авиабилеты на субботу |
| 74 | ru | flights | flights | yes | Рейсы по цене |
| 75 | ru | shopping | shopping | yes | Покажи ноутбуки |
| 76 | ru | shopping | shopping | yes | Беспроводные наушники до 100 AZN |
| 77 | ru | shopping | shopping | yes | Добавь P010 в корзину |
| 78 | ru | shopping | shopping | yes | Удали P001 из корзины |
| 79 | ru | shopping | shopping | yes | Товары Sonivo |
| 80 | ru | shopping | shopping | yes | Сравни P003 и P004 |
| 81 | ru | shopping | shopping | yes | Чёрные беговые кроссовки |
| 82 | ru | shopping | shopping | yes | Подарок до 50 AZN |
| 83 | ru | cinema | cinema | yes | Что идёт в кино сегодня вечером? |
| 84 | ru | cinema | cinema | yes | Фантастика на английском в субботу |
| 85 | ru | cinema | cinema | yes | Есть места на Orbit Zero? |
| 86 | ru | cinema | cinema | yes | Забронируй два билета S001 |
| 87 | ru | cinema | cinema | yes | Сеансы CinemaPlus 28 Mall |
| 88 | ru | cinema | cinema | yes | Фильмы с рейтингом выше 8 |
| 89 | ru | mixed | mixed | yes | Рейс в Стамбул и рюкзак для поездки |
| 90 | ru | mixed | mixed | yes | Наушники и билеты в кино |
| 91 | ru | mixed | mixed | yes | Рейс, ноутбук и фильм |
| 92 | ru | ambiguous | ambiguous | yes | Покажи что-нибудь хорошее |
| 93 | ru | ambiguous | ambiguous | yes | Забронируй два места |
| 94 | ru | out_of_scope | out_of_scope | yes | Какая погода в Гяндже? |
| 95 | ru | out_of_scope | out_of_scope | yes | Напиши код на Python |
| 96 | ru | follow_up | follow_up | yes | Тот, что дешевле |
| 97 | ru | follow_up | follow_up | yes | А в субботу? |
| 98 | ru | follow_up | follow_up | yes | Второй вариант |
| 99 | ru | ambiguous | ambiguous | yes | Забронируй его |
| 100 | mixed | mixed | mixed | yes | Friday uçuş Istanbul və black backpack |
| 101 | mixed | shopping | shopping | yes | Наушники under 100 AZN |
| 102 | mixed | cinema | cinema | yes | Sabah кино var? |
| 103 | en | shopping | ambiguous | no | Looking for cans for my commute |
| 104 | en | cinema | ambiguous | no | I want to catch a flick |
| 105 | ru | flights | ambiguous | no | Мне нужен перелёт в Париж |
| 106 | az | shopping | ambiguous | no | Mənə qulaq üçün yaxşı bir cihaz lazımdır |

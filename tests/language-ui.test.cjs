const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

// Exercise the real page script with a minimal DOM and controlled API responses.
// No browser, external service, or dependency is required.
async function page(storage = new Map([
  ["superchat.language", "en"], ["superchat.session", "old"],
])) {
  const elements = new Map();
  const element = () => ({
    value: "", checked: false, children: [], open: false,
    showModal() { this.open = true; },
    close(value = "") { this.returnValue = value; this.open = false; this.onclose?.(); },
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    addEventListener() {}, setAttribute() {}, focus() {}, remove() {},
    insertAdjacentHTML() {}, append(child) { this.children.push(child); },
  });
  const select = (selector) => {
    if (!elements.has(selector)) elements.set(selector, element());
    return elements.get(selector);
  };
  const old = {
    id: "old", title: "Saved Azerbaijani chat", messages: [], source: null,
    state: { language: "az", cart: {}, reservations: [], domains: {} },
  };
  const result = { session: old, reply: { language: "az", text: "", sections: [] } };
  const requests = [];
  const handlers = { message: () => result, image: () => result, delete: () => ({deleted: "old"}), getSession: () => old };
  const document = {
    documentElement: {}, querySelector: select, querySelectorAll: () => [],
    addEventListener() {}, createElement: element,
  };
  const context = vm.createContext({
    document, window: { addEventListener() {}, confirm: () => false },
    localStorage: { getItem: (key) => storage.get(key) ?? null,
      setItem: (key, value) => storage.set(key, value), removeItem: (key) => storage.delete(key) },
    FormData, URL, crypto, setTimeout, clearTimeout,
    fetch: async (url, options) => {
      requests.push({ url, ...options });
      let body;
      if (options?.method === "DELETE") body = await handlers.delete(url);
      else if (url.endsWith("/messages")) body = await handlers.message(options);
      else if (url.endsWith("/images")) body = await handlers.image(options);
      else if (url === "/api/config") body = { reference_date: "2026-11-02" };
      else if (url === "/api/sessions") body = [old];
      else if (url.startsWith("/api/sessions/")) body = await handlers.getSession(url);
      else throw Error(`Unexpected request ${url}`);
      return { ok: true, json: async () => body };
    },
  });
  await vm.runInContext(readFileSync(resolve(__dirname, "../superchat/static/app.js"), "utf8"), context);
  function choose(language) {
    select("#language").value = language;
    select("#language").onchange();
  }
  return { context, select, choose, document, storage, requests, handlers, result };
}

test("saved English choice survives opening an Azerbaijani session and reload", async () => {
  const p = await page();
  assert.equal(p.document.documentElement.lang, "en");
  p.choose("ru");
  const reloaded = await page(p.storage);
  assert.equal(reloaded.select("#language").value, "ru");
  assert.equal(reloaded.document.documentElement.lang, "ru");
});

test("sending text uses the selector and a response cannot overwrite it", async () => {
  const p = await page();
  p.choose("az");
  p.choose("en");
  await p.context.send("something");
  const request = p.requests.find((r) => r.url.endsWith("/messages"));
  assert.equal(JSON.parse(request.body).language, "en");
  assert.equal(p.select("#language").value, "en");
  assert.equal(p.storage.get("superchat.language"), "en");
});

test("a language selected during a pending reply stays selected", async () => {
  const p = await page();
  let finish;
  p.handlers.message = () => new Promise((resolve) => { finish = resolve; });
  const sending = p.context.send("something");
  p.choose("ru");
  finish(p.result);
  await sending;
  assert.equal(p.document.documentElement.lang, "ru");
  assert.equal(p.storage.get("superchat.language"), "ru");
});

test("image uploads carry the current language", async () => {
  const p = await page();
  p.choose("en");
  await p.context.upload(new File(["image"], "test.png", { type: "image/png" }));
  const request = p.requests.find((r) => r.url.endsWith("/images"));
  assert.equal(request.body.get("language"), "en");
  assert.equal(p.document.documentElement.lang, "en");
});

test("retry preserves the original request language without resetting the selector", async () => {
  const p = await page();
  p.handlers.message = () => { throw Error("Connection lost"); };
  await p.context.send("something");
  p.choose("ru");
  p.handlers.message = () => p.result;
  await p.select("#notice").children.at(-1).onclick();
  const sent = p.requests.filter((r) => r.url.endsWith("/messages"));
  assert.equal(sent.length, 2);
  assert.deepEqual(JSON.parse(sent[0].body), JSON.parse(sent[1].body));
  assert.equal(p.document.documentElement.lang, "ru");
});

test("snapshot cards show unknown inventory and never offer a reservation button", async () => {
  const p = await page();
  const card = { id: "AV-123", kind: "flights", title: "Baku → Istanbul", subtitle: "Airline",
    price: 100, available: null, fields: [{label: "baggage", value: null}],
    snapshot: true, availability: "unknown", source: "aviasales.az",
    source_url: "https://www.aviasales.az/search/example", fetched_at: "2026-11-02T10:00:00+04:00",
    price_scope: "entire_round_trip", stale: true };
  const html = p.context.cardHTML(card);
  assert.match(html, /Availability unverified/);
  assert.match(html, /Not published/);
  assert.match(html, /Round-trip total/);
  assert.match(html, /Older snapshot/);
  assert.match(html, /View source/);
  assert.match(html, /data-prompt="Save AV-123 to my plans"/);
  assert.match(html, /Save to plans/);
  assert.doesNotMatch(html, />Reserve<|>Unavailable</);
  const unsafe = p.context.cardHTML({...card, source_url: "javascript:alert(1)"});
  assert.doesNotMatch(unsafe, /href="javascript:/);
});

test("conflicting cinema prices remain visible and truncated results are explained", async () => {
  const p = await page();
  const card = { id: "CM-S-test", kind: "cinema", title: "Film", subtitle: "Cinema",
    price: 20, available: null, fields: [], snapshot: true, availability: "unknown",
    source: "cinemastercard.az", price_conflict: true,
    price_observations: [{price_azn: 15, source_url: "https://example.com/venue"}, {price_azn: 20, source_url: "https://example.com/movie"}] };
  const html = p.context.replyHTML({sections: [{domain: "cinema", text: "Results", total_matches: 531, cards: [card]}]});
  assert.match(html, /Source prices disagree/);
  assert.match(html, /15 AZN/);
  assert.match(html, /20 AZN/);
  assert.match(html, /Showing 1 of 531/);
});

test("database source links and similarity remain clear in all three languages", async () => {
  const p = await page();
  vm.runInContext('config = {data_mode: "database"}', p.context);
  const card = {id: "BM-123", kind: "shopping", title: "Laptop", subtitle: "Brand", price: 120,
    fields: [], snapshot: true, similarity: .91, source: "birmarket.az",
    source_url: "https://birmarket.az/product/123-laptop", source_title: "Notbuk"};
  for (const [lang, label] of [["en","Open Birmarket"],["az","Birmarket-də aç"],["ru","Открыть Birmarket"]]) {
    p.choose(lang);
    const html = p.context.cardHTML(card);
    assert.match(html, new RegExp(label));
    assert.match(html, /href="https:\/\/birmarket.az\/product\/123-laptop"/);
    assert.match(html, /target="_blank" rel="noopener noreferrer"/);
    assert.match(html, /0.91/);
    assert.doesNotMatch(html, /91%/);
  }
  p.choose("en");
  assert.equal(vm.runInContext('t("demo")',p.context),"REAL CATALOGUE");
});

test("rejected credentials have a distinct localized notice", async () => {
  const p = await page();
  for (const [lang, phrase] of [["en", "rejected the connection credentials"], ["az", "qoşulma məlumatlarını qəbul etmədi"], ["ru", "отклонил данные доступа"]]) {
    p.choose(lang);
    const html = p.context.replyHTML({sections: [], notice: "ai_auth_failed"});
    assert.ok(html.includes(phrase));
    assert.doesNotMatch(html, /OpenRouter|API_KEY/);
  }
});

test("saved plans render titles, source links, removal and an unconfirmed label", async () => {
  const p = await page();
  const saved = {status:"saved_local", item_id:"CM-S-123", title:"Film", subtitle:"Deniz Mall", quantity:1, unit_price:null, source_url:"https://cinemastercard.az/movie/123"};
  for (const [lang, phrase] of [["en","not booked"],["az","bron edilməyib"],["ru","не забронировано"]]) {
    p.choose(lang);
    const html = p.context.savedPlanHTML(saved, true);
    assert.ok(html.includes(phrase));
    assert.match(html, /Deniz Mall/);
    assert.match(html, /data-prompt=/);
    assert.match(html, /https:\/\/cinemastercard.az\/movie\/123/);
    assert.doesNotMatch(html, /undefined|NaN|SC-/);
  }
  assert.doesNotMatch(p.context.savedPlanHTML({...saved,source_url:"javascript:alert(1)"}), /href=/);
  assert.match(p.context.replyHTML({text:"Hello",sections:[]}), /Bir SuperChat/);
});

test("deleting a chat requires confirmation and clears the last active conversation", async () => {
  const p = await page();
  let deletion = p.context.deleteSession("old");
  assert.equal(p.select("#delete-dialog").open, true);
  assert.match(p.select("#delete-description").textContent, /permanently deleted/);
  p.select("#delete-cancel").onclick();
  await deletion;
  assert.equal(p.requests.filter(r => r.method === "DELETE").length, 0);
  deletion = p.context.deleteSession("old");
  p.select("#delete-confirm").onclick();
  await deletion;
  assert.equal(p.requests.filter(r => r.method === "DELETE").length, 1);
  assert.equal(p.storage.has("superchat.session"), false);
  assert.equal(p.storage.get("superchat.language"), "en");
  assert.equal(p.select("#messages").innerHTML, "");
  assert.equal(p.select("#welcome").hidden, false);
  assert.equal(p.select("#booking-count").textContent, 0);
  assert.equal(p.select("#cart-count").textContent, 0);
  assert.equal(vm.runInContext('session',p.context), null);
});

test("failed deletion preserves the current chat", async () => {
  const p = await page();
  p.handlers.delete = () => { throw Error("Connection lost"); };
  const deletion = p.context.deleteSession("old");
  p.select("#delete-confirm").onclick();
  await deletion;
  assert.equal(p.storage.get("superchat.session"), "old");
  assert.equal(vm.runInContext('session.id',p.context), "old");
  assert.equal(p.select("#notice").textContent, "Connection lost");
});

test("deleting the active chat opens a remaining chat", async () => {
  const p = await page();
  const other = {id:"other",title:"Other chat",messages:[],source:null,state:{cart:{},reservations:[],domains:{}}};
  p.context.other = other;
  vm.runInContext('sessions.push(other)',p.context);
  p.handlers.getSession = () => other;
  const deletion = p.context.deleteSession("old");
  p.select("#delete-confirm").onclick();
  await deletion;
  assert.equal(p.storage.get("superchat.session"), "other");
  assert.equal(vm.runInContext('session.id',p.context), "other");
});

test("chat deletion labels are localized and all logo marks use B", async () => {
  const p = await page();
  for (const [lang,label] of [["en","Delete chat"],["az","Söhbəti sil"],["ru","Удалить чат"]]) {
    p.choose(lang);
    p.context.renderSessions();
    assert.ok(p.select("#session-list").innerHTML.includes(label));
    assert.match(p.select("#session-list").innerHTML, /data-delete-session="old"/);
  }
  assert.match(p.context.replyHTML({sections:[]}), /class="brand-mark">B</);
  assert.match(readFileSync(resolve(__dirname,"../superchat/static/index.html"),"utf8"), /class="brand-mark">B</);
  assert.match(readFileSync(resolve(__dirname,"../superchat/static/favicon.svg"),"utf8"), />B<\/text>/);
});

test("delete dialog localizes its actions and safely displays the chat title", async () => {
  const p = await page();
  for (const [language,cancel,remove] of [["en","Cancel","Delete chat"],["az","Ləğv et","Söhbəti sil"],["ru","Отмена","Удалить чат"]]) {
    p.choose(language);
    const result = p.context.confirmChatDeletion('<img src=x onerror=alert(1)>');
    assert.equal(p.select('#delete-chat-title').textContent, '<img src=x onerror=alert(1)>');
    assert.equal(p.select('#delete-cancel').textContent, cancel);
    assert.equal(p.select('#delete-confirm').textContent, remove);
    assert.equal(await p.context.confirmChatDeletion('Another chat'), false);
    p.select('#delete-dialog').close();
    assert.equal(await result, false);
  }
  assert.equal(p.requests.filter(r => r.method === 'DELETE').length, 0);
});

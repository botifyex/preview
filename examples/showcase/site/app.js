const SESSION_KEY = "mossbill.session";
const CART_KEY = "mossbill.cart";
const NAVIGATION = [
  ["index", "Dashboard"], ["invoices", "Invoices"], ["reports", "Statements"],
  ["addons", "Add-ons"], ["settings", "Settings"],
];

const money = (amount) =>
  "$" + amount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const cart = () => JSON.parse(localStorage.getItem(CART_KEY) || "[]");
const saveCart = (items) => localStorage.setItem(CART_KEY, JSON.stringify(items));
const statusChip = (status) => `<span class="chip chip-${status.toLowerCase()}">${status}</span>`;
const isTouch = () => matchMedia("(pointer: coarse)").matches;

function shell(page, content) {
  const links = NAVIGATION.map(([target, name]) =>
    `<a class="nav-link${target === page ? " active" : ""}" href="${target}.html">${name}</a>`).join("");
  document.body.insertAdjacentHTML("afterbegin", `
    <aside class="sidebar" aria-label="Sidebar">
      <p class="brand"><span class="brand-mark">M</span> Mossbill</p>
      <nav aria-label="Main">${links}</nav>
      <p class="sidebar-foot">Demo workspace</p>
    </aside>
    <div class="workspace">
      <header class="topbar">
        <button class="button icon menu-button" type="button" aria-label="Menu" id="menu-button">☰</button>
        <p class="workspace-name">Fernhill Accounting <span class="muted">(fictional)</span></p>
        <a class="button ghost" id="cart-link" href="cart.html">Cart (${cart().length})</a>
        <button class="button icon" type="button" aria-label="Notifications">🔔</button>
        <span class="avatar" aria-label="Signed in as Demo User">DU</span>
      </header>
      <main class="content">${content}</main>
    </div>
    <div class="dev-overlay${new URLSearchParams(location.search).get("devtools") === "pinned" ? " pinned" : ""}">
      dev build · 14 ms · 3 warnings
    </div>
    <div class="toast" id="toast" role="status" hidden></div>`);
  document.getElementById("menu-button").addEventListener("click", () => document.body.classList.toggle("menu-open"));
}

function dashboard() {
  const bars = REVENUE.map(([month, value], index) => {
    const height = value * 3;
    return `<rect x="${index * 76 + 18}" y="${170 - height}" width="44" height="${height}" rx="6"></rect>
      <text x="${index * 76 + 40}" y="190" text-anchor="middle">${month}</text>`;
  }).join("");
  const rows = INVOICES.slice(0, 4).map(invoiceRow).join("");
  return `
    <div class="title-row">
      <h1>Dashboard</h1>
      <a class="button primary" href="invoices.html">New invoice</a>
    </div>
    <section class="tiles" aria-label="Summary">
      <article class="tile"><h2>Revenue this month</h2><p class="figure-value">$48,250</p><p class="trend up">+4.6% on September</p></article>
      <article class="tile"><h2>Outstanding</h2><p class="figure-value">$12,480</p><p class="muted small">6 invoices</p></article>
      <article class="tile"><h2>Late payments</h2><p class="figure-value alert">3</p><p class="muted small">$6,784.65 past due</p></article>
      <article class="tile"><h2>Active customers</h2><p class="figure-value">128</p><p class="muted small">9 joined this quarter</p></article>
    </section>
    <section class="split">
      <article class="panel" id="revenue-chart">
        <h2>Revenue, thousand dollars</h2>
        <svg viewBox="0 0 480 200" role="img" aria-label="Revenue chart">${bars}</svg>
      </article>
      <article class="panel" id="next-up">
        <h2>Next up</h2>
        <ul class="plain-list">
          <li><strong>3 reminders</strong> go out tomorrow</li>
          <li><strong>Q3 tax report</strong> is ready to review</li>
          <li><strong>2 customers</strong> changed their address</li>
        </ul>
      </article>
    </section>
    <section class="panel table-panel">
      <h2>Recent invoices</h2>
      <table><tbody>${rows}</tbody></table>
    </section>`;
}

function invoiceRow(invoice) {
  return `<tr data-status="${invoice.status}" data-number="${invoice.number}">
    <td><a class="invoice-link" href="invoice.html?id=${invoice.number}">${invoice.number}</a></td>
    <td class="customer">${invoice.customer}</td>
    <td class="narrow-hidden">${invoice.issued}</td>
    <td class="narrow-hidden">${invoice.due}</td>
    <td class="amount">${money(invoice.amount)}</td>
    <td>${statusChip(invoice.status)}</td>
    <td class="row-actions narrow-hidden"><span class="row-buttons"><button class="button small-button" type="button">Remind</button><button class="button small-button" type="button">Copy</button></span></td>
  </tr>`;
}

function invoices() {
  const pills = ["All", "Paid", "Open", "Overdue"].map((status, index) => {
    const count = status === "All" ? INVOICES.length : INVOICES.filter((invoice) => invoice.status === status).length;
    return `<button class="pill${index ? "" : " active"}" type="button" data-filter="${status}">${status} · ${count}</button>`;
  }).join("");
  return `
    <div class="title-row">
      <h1>Invoices</h1>
      <button class="button ghost" type="button" id="export">Export CSV</button>
    </div>
    <div class="toolbar">
      <label class="visually-hidden" for="search">Search invoices</label>
      <input id="search" type="search" placeholder="Search by customer or number">
      <div class="pills" role="group" aria-label="Status">${pills}</div>
    </div>
    <p class="swipe-hint">Swipe a row left to send a reminder</p>
    <section class="panel table-panel">
      <table>
        <thead><tr><th>Number</th><th class="customer">Customer</th><th class="narrow-hidden">Issued</th><th class="narrow-hidden">Due</th><th class="amount">Amount</th><th>Status</th><th class="narrow-hidden"></th></tr></thead>
        <tbody>${INVOICES.map(invoiceRow).join("")}</tbody>
      </table>
    </section>
    <p class="muted small results-count" id="results">${INVOICES.length} invoices</p>`;
}

function bindInvoices() {
  let filter = "All";
  const search = document.getElementById("search");
  const apply = () => {
    const words = search.value.toLowerCase();
    let shown = 0;
    document.querySelectorAll("tbody tr").forEach((row) => {
      const visible = (filter === "All" || row.dataset.status === filter) && row.textContent.toLowerCase().includes(words);
      row.hidden = !visible;
      shown += visible ? 1 : 0;
    });
    document.getElementById("results").textContent = `${shown} ${shown === 1 ? "invoice" : "invoices"}`;
  };
  search.addEventListener("keydown", (event) => event.key === "Enter" && apply());
  document.querySelectorAll(".pill").forEach((pill) => pill.addEventListener("click", () => {
    document.querySelector(".pill.active").classList.remove("active");
    pill.classList.add("active");
    filter = pill.dataset.filter;
    apply();
  }));
  document.getElementById("export").addEventListener("click", () => notify("Export started: 14 rows"));
}

function invoiceDetail() {
  const number = new URLSearchParams(location.search).get("id") || "INV-1042";
  const invoice = INVOICES.find((item) => item.number === number) || INVOICES[6];
  const rows = LINE_ITEMS.map(([name, quantity, price]) =>
    `<tr><td>${name}</td><td class="amount">${quantity}</td><td class="amount">${money(price)}</td><td class="amount">${money(quantity * price)}</td></tr>`).join("");
  const subtotal = LINE_ITEMS.reduce((sum, [, quantity, price]) => sum + quantity * price, 0);
  return `
    <p class="crumb"><a href="invoices.html">← All invoices</a></p>
    <div class="title-row">
      <h1>${invoice.number}</h1>
      ${statusChip(invoice.status)}
      <span class="spacer"></span>
      <button class="button ghost" type="button">Download PDF</button>
      <button class="button primary" type="button" id="remind">Send reminder</button>
    </div>
    <section class="split even" id="parties">
      <article class="panel" id="bill-from"><h2>From</h2><p><strong>Fernhill Accounting</strong><br>12 Sample Street, Testville</p></article>
      <article class="panel" id="bill-to"><h2>Bill to</h2><p><strong>${invoice.customer}</strong><br>4 Placeholder Road, Demoford</p></article>
    </section>
    <section class="panel table-panel" id="line-items">
      <h2>Line items</h2>
      <table>
        <thead><tr><th>Service</th><th class="amount">Qty</th><th class="amount">Price</th><th class="amount">Total</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <dl class="totals">
        <div id="subtotal"><dt>Subtotal</dt><dd>${money(subtotal)}</dd></div>
        <div id="tax"><dt>Tax 10%</dt><dd>${money(subtotal * 0.1)}</dd></div>
        <div id="total"><dt>Total due</dt><dd>${money(subtotal * 1.1)}</dd></div>
      </dl>
    </section>
    <section class="split even">
      <article class="panel" id="timeline">
        <h2>History</h2>
        <ol class="plain-list">
          <li><strong>Sep 18</strong> Invoice sent</li>
          <li><strong>Sep 19</strong> Opened by customer</li>
          <li><strong>Oct 18</strong> Due date passed</li>
        </ol>
      </article>
      <article class="panel" id="payment-terms">
        <h2>Payment terms</h2>
        <p>Pay within <span id="term-days">30 days</span> by bank transfer. Late invoices carry a <span id="late-fee">2% fee</span> each month.</p>
      </article>
    </section>`;
}

function statements() {
  const tiles = STATEMENTS.map(([month, amount]) =>
    `<article class="tile statement" data-month="${month}"><h2>${month}</h2><p class="figure-value small-value">$${amount.toLocaleString("en-US")}</p></article>`).join("");
  return `<div class="title-row"><h1>Statements</h1></div><section class="statements">${tiles}</section>`;
}

function addons() {
  const inCart = cart();
  const cards = ADDONS.map((addon) => `
    <article class="tile addon">
      <h2>${addon.name}</h2>
      <p class="muted">${addon.description}</p>
      <p class="addon-foot"><strong>$${addon.price}/mo</strong>
        <button class="button primary" type="button" data-addon="${addon.name}" aria-label="Add ${addon.name}">${inCart.includes(addon.name) ? "Added" : "Add"}</button>
      </p>
    </article>`).join("");
  return `<div class="title-row"><h1>Add-ons</h1></div><section class="addons">${cards}</section>`;
}

function bindAddons() {
  document.querySelectorAll("[data-addon]").forEach((button) => button.addEventListener("click", () => {
    saveCart([...new Set([...cart(), button.dataset.addon])]);
    button.textContent = "Added";
    document.getElementById("cart-link").textContent = `Cart (${cart().length})`;
    notify(`${button.dataset.addon} added to cart`);
  }));
}

function cartPage() {
  const chosen = ADDONS.filter((addon) => cart().includes(addon.name));
  if (!chosen.length) {
    return `<div class="title-row"><h1>Cart</h1></div><section class="panel"><p>Your cart is empty.</p></section>`;
  }
  const rows = chosen.map((addon) => `<tr><td>${addon.name}</td><td class="amount">$${addon.price}/mo</td></tr>`).join("");
  const total = chosen.reduce((sum, addon) => sum + addon.price, 0);
  return `
    <div class="title-row"><h1>Cart</h1></div>
    <section class="panel table-panel cart-panel" id="cart-panel">
      <table><tbody>${rows}<tr class="total-row"><td>Total</td><td class="amount">$${total}/mo</td></tr></tbody></table>
      <p class="cart-actions"><button class="button primary" type="button" id="place-order">Place order</button></p>
    </section>`;
}

function bindCart() {
  document.getElementById("place-order")?.addEventListener("click", () => {
    const names = cart().join(", ");
    saveCart([]);
    document.getElementById("cart-link").textContent = "Cart (0)";
    document.querySelector(".content").innerHTML = `
      <div class="title-row"><h1>Order confirmed</h1></div>
      <section class="panel confirmation"><p class="check">✓</p>
        <p>Order <strong>MB-2048</strong> is active: ${names}.</p>
        <p class="muted">This demo charges nothing.</p></section>`;
  });
}

function settings() {
  return `
    <div class="title-row"><h1>Settings</h1><button class="button primary" type="button" id="save">Save changes</button></div>
    <section class="split even">
      <form class="panel form-panel" id="profile" onsubmit="return false">
        <h2>Profile</h2>
        <label for="work-email">Work email</label><input id="work-email" type="email" value="demo@mossbill.example">
        <label for="name">Full name</label><input id="name" value="Demo User">
        <label for="company">Company</label><input id="company" value="Fernhill Accounting">
      </form>
      <section class="panel form-panel" id="notifications">
        <h2>Notifications</h2>
        <label class="switch"><input type="checkbox" checked> Invoice paid</label>
        <label class="switch"><input type="checkbox" checked> Invoice overdue</label>
        <label class="switch"><input type="checkbox"> Weekly summary</label>
        <label for="currency">Currency</label>
        <select id="currency"><option>US dollar</option><option>Euro</option></select>
      </section>
    </section>`;
}

function notify(message) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.hidden = false;
}

function bindSettings() {
  document.getElementById("save").addEventListener("click", () => notify("Settings saved"));
}

const PAGES = {
  index: [dashboard],
  invoices: [invoices, bindInvoices],
  invoice: [invoiceDetail],
  reports: [statements],
  addons: [addons, bindAddons],
  cart: [cartPage, bindCart],
  settings: [settings, bindSettings],
};

function start() {
  if (!localStorage.getItem(SESSION_KEY)) {
    location.replace("login.html");
    return;
  }
  const page = document.body.dataset.page;
  const [render, bind] = PAGES[page];
  shell(page, render());
  bind?.();
  if (isTouch()) document.body.classList.add("touch");
}

start();

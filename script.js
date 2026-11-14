const products = [
  { id: 1, name: "Nasi Ayam Sambal Matah", category: "Makanan", price: 28000, rating: "4.9", badge: "Terlaris", image: "https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=700&q=80" },
  { id: 2, name: "Pizza Margherita", category: "Pizza", price: 58000, rating: "4.8", badge: "Favorit", image: "https://images.unsplash.com/photo-1579751626657-72bc17010498?auto=format&fit=crop&w=700&q=80" },
  { id: 3, name: "Classic Beef Burger", category: "Burger", price: 42000, rating: "4.9", badge: "Best seller", image: "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=700&q=80" },
  { id: 4, name: "Es Kopi Gula Aren", category: "Minuman", price: 18000, rating: "4.7", badge: "Segar", image: "https://images.unsplash.com/photo-1461023058943-07fcbe16d735?auto=format&fit=crop&w=700&q=80" },
  { id: 5, name: "Pasta Creamy Mushroom", category: "Makanan", price: 39000, rating: "4.8", badge: "Baru", image: "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?auto=format&fit=crop&w=700&q=80" },
  { id: 6, name: "Chicken Pepperoni Pizza", category: "Pizza", price: 62000, rating: "4.9", badge: "Favorit", image: "https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=700&q=80" },
  { id: 7, name: "Strawberry Cheesecake", category: "Dessert", price: 25000, rating: "4.8", badge: "Manisnya pas", image: "https://images.unsplash.com/photo-1533134242443-d4fd215305ad?auto=format&fit=crop&w=700&q=80" },
  { id: 8, name: "Jus Jeruk Segar", category: "Minuman", price: 15000, rating: "4.7", badge: "Fresh", image: "https://images.unsplash.com/photo-1600271886742-f049cd451bba?auto=format&fit=crop&w=700&q=80" },
];

const productGrid = document.querySelector("#product-grid");
const searchInput = document.querySelector("#search-input");
const cartDrawer = document.querySelector("#cart-drawer");
const overlay = document.querySelector("#overlay");
const cartItems = document.querySelector("#cart-items");
const cartEmpty = document.querySelector("#cart-empty");
const cartSummary = document.querySelector("#cart-summary");
const cart = new Map();
let activeCategory = "Semua";
let toastTimer;

const formatPrice = (price) => new Intl.NumberFormat("id-ID", {
  style: "currency",
  currency: "IDR",
  maximumFractionDigits: 0,
}).format(price);

function renderProducts() {
  const query = searchInput.value.trim().toLocaleLowerCase("id");
  const filtered = products.filter((product) => {
    const matchesCategory = activeCategory === "Semua" || product.category === activeCategory;
    return matchesCategory && product.name.toLocaleLowerCase("id").includes(query);
  });

  productGrid.innerHTML = filtered.length
    ? filtered.map((product) => `
      <article class="product-card">
        <div class="product-image">
          <img src="${product.image}" alt="${product.name}" loading="lazy">
          <span class="product-badge">${product.badge}</span>
        </div>
        <div class="product-info">
          <div class="product-meta"><span>${product.category}</span><span class="product-rating">★ ${product.rating}</span></div>
          <h3 class="product-name">${product.name}</h3>
          <div class="product-bottom">
            <div class="product-price"><small>Harga</small>${formatPrice(product.price)}</div>
            <button class="add-button" type="button" data-add="${product.id}" aria-label="Tambah ${product.name} ke keranjang">+</button>
          </div>
        </div>
      </article>
    `).join("")
    : '<p class="no-results">Yah, makanan yang kamu cari belum ada. Coba kata kunci lain, ya.</p>';
}

function renderCart() {
  const entries = [...cart.entries()];
  const itemCount = entries.reduce((total, [, quantity]) => total + quantity, 0);
  const subtotal = entries.reduce((total, [id, quantity]) => {
    const product = products.find((item) => item.id === id);
    return total + product.price * quantity;
  }, 0);

  document.querySelector("#cart-count").textContent = itemCount;
  document.querySelector("#cart-subtotal").textContent = formatPrice(subtotal);
  document.querySelector("#cart-total").textContent = formatPrice(subtotal);
  cartEmpty.classList.toggle("visible", entries.length === 0);
  cartSummary.classList.toggle("hidden", entries.length === 0);
  cartItems.innerHTML = entries.map(([id, quantity]) => {
    const product = products.find((item) => item.id === id);
    return `
      <article class="cart-item">
        <img src="${product.image}" alt="">
        <div>
          <h3>${product.name}</h3>
          <span class="cart-item-price">${formatPrice(product.price)}</span>
          <div class="quantity-control">
            <button type="button" data-quantity="${id}" data-change="-1" aria-label="Kurangi ${product.name}">−</button>
            <span>${quantity}</span>
            <button type="button" data-quantity="${id}" data-change="1" aria-label="Tambah ${product.name}">+</button>
          </div>
        </div>
        <button class="remove-item" type="button" data-remove="${id}" aria-label="Hapus ${product.name}">×</button>
      </article>
    `;
  }).join("");
}

function showToast(message) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove("show"), 2400);
}

function setCartOpen(isOpen) {
  cartDrawer.classList.toggle("open", isOpen);
  overlay.classList.toggle("visible", isOpen);
  cartDrawer.setAttribute("aria-hidden", String(!isOpen));
  document.body.style.overflow = isOpen ? "hidden" : "";
}

document.querySelector("#category-list").addEventListener("click", (event) => {
  const button = event.target.closest("[data-category]");
  if (!button) return;
  activeCategory = button.dataset.category;
  document.querySelectorAll(".category-chip").forEach((chip) => {
    chip.classList.toggle("active", chip === button);
  });
  renderProducts();
});

searchInput.addEventListener("input", renderProducts);

productGrid.addEventListener("click", (event) => {
  const button = event.target.closest("[data-add]");
  if (!button) return;
  const id = Number(button.dataset.add);
  cart.set(id, (cart.get(id) || 0) + 1);
  renderCart();
  showToast(`${products.find((item) => item.id === id).name} ditambahkan ke keranjang`);
});

cartItems.addEventListener("click", (event) => {
  const quantityButton = event.target.closest("[data-quantity]");
  const removeButton = event.target.closest("[data-remove]");
  if (quantityButton) {
    const id = Number(quantityButton.dataset.quantity);
    const nextQuantity = (cart.get(id) || 0) + Number(quantityButton.dataset.change);
    if (nextQuantity <= 0) cart.delete(id);
    else cart.set(id, nextQuantity);
    renderCart();
  }
  if (removeButton) {
    cart.delete(Number(removeButton.dataset.remove));
    renderCart();
  }
});

document.querySelector("#open-cart").addEventListener("click", () => setCartOpen(true));
document.querySelector("#close-cart").addEventListener("click", () => setCartOpen(false));
overlay.addEventListener("click", () => setCartOpen(false));
document.querySelector("#browse-menu").addEventListener("click", () => {
  setCartOpen(false);
  document.querySelector("#menu").scrollIntoView({ behavior: "smooth" });
});
document.querySelector("#checkout-button").addEventListener("click", () => {
  if (cart.size === 0) return;
  cart.clear();
  renderCart();
  setCartOpen(false);
  showToast("Pesanan demo berhasil dibuat. Terima kasih! 🎉");
});
document.querySelector("#menu-toggle").addEventListener("click", () => {
  document.querySelector(".main-nav").classList.toggle("open");
});
document.querySelectorAll(".nav-link").forEach((link) => {
  link.addEventListener("click", () => document.querySelector(".main-nav").classList.remove("open"));
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") setCartOpen(false);
});

renderProducts();
renderCart();

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price INTEGER NOT NULL CHECK (price >= 0),
    rating TEXT NOT NULL,
    badge TEXT NOT NULL,
    image TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY,
    idempotency_key UUID NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending',
    total BIGINT NOT NULL CHECK (total >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS order_items (
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL CHECK (quantity BETWEEN 1 AND 50),
    unit_price INTEGER NOT NULL CHECK (unit_price >= 0),
    PRIMARY KEY (order_id, product_id)
);

CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders (created_at DESC);

INSERT INTO products (id, name, category, price, rating, badge, image) VALUES
    (1, 'Nasi Ayam Sambal Matah', 'Makanan', 28000, '4.9', 'Terlaris', 'https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=700&q=80'),
    (2, 'Pizza Margherita', 'Pizza', 58000, '4.8', 'Favorit', 'https://images.unsplash.com/photo-1579751626657-72bc17010498?auto=format&fit=crop&w=700&q=80'),
    (3, 'Classic Beef Burger', 'Burger', 42000, '4.9', 'Best seller', 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=700&q=80'),
    (4, 'Es Kopi Gula Aren', 'Minuman', 18000, '4.7', 'Segar', 'https://images.unsplash.com/photo-1461023058943-07fcbe16d735?auto=format&fit=crop&w=700&q=80'),
    (5, 'Pasta Creamy Mushroom', 'Makanan', 39000, '4.8', 'Baru', 'https://images.unsplash.com/photo-1473093295043-cdd812d0e601?auto=format&fit=crop&w=700&q=80'),
    (6, 'Chicken Pepperoni Pizza', 'Pizza', 62000, '4.9', 'Favorit', 'https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=700&q=80'),
    (7, 'Strawberry Cheesecake', 'Dessert', 25000, '4.8', 'Manisnya pas', 'https://images.unsplash.com/photo-1533134242443-d4fd215305ad?auto=format&fit=crop&w=700&q=80'),
    (8, 'Jus Jeruk Segar', 'Minuman', 15000, '4.7', 'Fresh', 'https://images.unsplash.com/photo-1600271886742-f049cd451bba?auto=format&fit=crop&w=700&q=80')
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    category = EXCLUDED.category,
    price = EXCLUDED.price,
    rating = EXCLUDED.rating,
    badge = EXCLUDED.badge,
    image = EXCLUDED.image,
    is_active = TRUE;

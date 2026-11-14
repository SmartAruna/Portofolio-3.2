import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID, uuid4

import asyncpg
import redis.asyncio as redis
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("rasaria")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ORDER_RATE_LIMIT = int(os.getenv("ORDER_RATE_LIMIT", "10"))
ORDER_RATE_WINDOW_SECONDS = int(os.getenv("ORDER_RATE_WINDOW_SECONDS", "60"))

PRODUCT_QUERY = """
    SELECT id, name, category, price, rating, badge, image
    FROM products
    WHERE is_active = TRUE
    ORDER BY id
"""

RATE_LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL wajib diatur sebelum API dijalankan.")
    app.state.db = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=2,
        max_size=int(os.getenv("DB_POOL_MAX_SIZE", "10")),
        command_timeout=10,
    )
    app.state.redis = redis.from_url(REDIS_URL, decode_responses=True)
    try:
        yield
    finally:
        await app.state.db.close()
        await app.state.redis.aclose()


app = FastAPI(title="RasaRia API", version="1.0.0", lifespan=lifespan)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Idempotency-Key"],
)


class OrderItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=50)


class OrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[OrderItem] = Field(min_length=1, max_length=20)

    @field_validator("items")
    @classmethod
    def product_ids_must_be_unique(cls, items: list[OrderItem]) -> list[OrderItem]:
        ids = [item.product_id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("Setiap produk hanya boleh muncul satu kali.")
        return items


def order_response(order: asyncpg.Record) -> dict:
    return {
        "id": str(order["id"]),
        "status": order["status"],
        "total": order["total"],
        "created_at": order["created_at"].isoformat(),
    }


@app.get("/api/health/live")
async def liveness():
    return {"status": "ok"}


@app.get("/api/health/ready")
async def readiness(request: Request):
    try:
        await request.app.state.db.fetchval("SELECT 1")
        await request.app.state.redis.ping()
    except (asyncpg.PostgresError, redis.RedisError) as exc:
        logger.warning("Readiness check failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Layanan belum siap.",
        ) from exc
    return {"status": "ready"}


@app.get("/api/products")
async def list_products(request: Request):
    cache = request.app.state.redis
    try:
        cached = await cache.get("products:active:v1")
        if cached is not None:
            return json.loads(cached)
    except (redis.RedisError, json.JSONDecodeError) as exc:
        logger.warning("Product cache read failed; using PostgreSQL: %s", exc)

    try:
        rows = await request.app.state.db.fetch(PRODUCT_QUERY)
    except asyncpg.PostgresError as exc:
        logger.exception("Could not load products")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Menu sementara tidak tersedia.",
        ) from exc

    products = [dict(row) for row in rows]
    try:
        await cache.set("products:active:v1", json.dumps(products), ex=60)
    except redis.RedisError as exc:
        logger.warning("Product cache write failed: %s", exc)
    return products


@app.post("/api/orders", status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderRequest,
    request: Request,
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=16, max_length=128),
    ] = None,
):
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header Idempotency-Key wajib diisi.",
        )
    try:
        idempotency_key = UUID(idempotency_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key harus berupa UUID.",
        ) from exc

    client_ip = request.client.host if request.client else "unknown"
    try:
        request_count = await request.app.state.redis.eval(
            RATE_LIMIT_SCRIPT,
            1,
            f"rate:orders:{client_ip}",
            ORDER_RATE_WINDOW_SECONDS,
        )
    except redis.RedisError as exc:
        logger.exception("Order rate limiter unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Checkout sementara tidak tersedia. Coba lagi sebentar.",
        ) from exc
    if request_count > ORDER_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Terlalu banyak percobaan checkout. Coba lagi dalam satu menit.",
            headers={"Retry-After": str(ORDER_RATE_WINDOW_SECONDS)},
        )

    item_ids = [item.product_id for item in payload.items]
    quantities = {item.product_id: item.quantity for item in payload.items}
    try:
        async with request.app.state.db.acquire() as connection:
            async with connection.transaction():
                products = await connection.fetch(
                    """
                    SELECT id, price
                    FROM products
                    WHERE id = ANY($1::integer[]) AND is_active = TRUE
                    """,
                    item_ids,
                )
                if len(products) != len(item_ids):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Satu atau lebih menu sudah tidak tersedia.",
                    )

                total = sum(row["price"] * quantities[row["id"]] for row in products)
                order_id = uuid4()
                order = await connection.fetchrow(
                    """
                    INSERT INTO orders (id, idempotency_key, status, total)
                    VALUES ($1, $2, 'pending', $3)
                    ON CONFLICT (idempotency_key) DO NOTHING
                    RETURNING id, status, total, created_at
                    """,
                    order_id,
                    idempotency_key,
                    total,
                )
                if order is None:
                    order = await connection.fetchrow(
                        """
                        SELECT id, status, total, created_at
                        FROM orders
                        WHERE idempotency_key = $1
                        """,
                        idempotency_key,
                    )
                    return order_response(order)

                await connection.executemany(
                    """
                    INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                    VALUES ($1, $2, $3, $4)
                    """,
                    [
                        (order_id, row["id"], quantities[row["id"]], row["price"])
                        for row in products
                    ],
                )
                return order_response(order)
    except asyncpg.PostgresError as exc:
        logger.exception("Could not create order")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pesanan belum dapat diproses. Silakan coba lagi.",
        ) from exc


@app.get("/{file_path:path}", include_in_schema=False)
async def frontend(file_path: str):
    if not file_path:
        file_path = "index.html"
    if file_path not in {"index.html", "style.css", "script.js"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File tidak ditemukan.")
    path = os.path.join(ROOT_DIR, file_path)
    return FileResponse(path)

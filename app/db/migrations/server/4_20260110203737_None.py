from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "categories" (
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(100) NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS "locations" (
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "id" SERIAL NOT NULL PRIMARY KEY,
    "city" VARCHAR(100) NOT NULL,
    "street" VARCHAR(255) NOT NULL,
    "house" VARCHAR(50) NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_locations_city_00624a" ON "locations" ("city");
CREATE TABLE IF NOT EXISTS "users" (
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "id" SERIAL NOT NULL PRIMARY KEY,
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "first_name" VARCHAR(100) NOT NULL,
    "last_name" VARCHAR(100) NOT NULL,
    "hashed_password" VARCHAR(255) NOT NULL
);
CREATE INDEX IF NOT EXISTS "idx_users_email_133a6f" ON "users" ("email");
CREATE TABLE IF NOT EXISTS "events" (
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "id" SERIAL NOT NULL PRIMARY KEY,
    "title" VARCHAR(255) NOT NULL,
    "short_description" TEXT NOT NULL,
    "full_description" TEXT NOT NULL,
    "date" DATE NOT NULL,
    "time" TIMETZ NOT NULL,
    "likes_count" INT NOT NULL  DEFAULT 0,
    "participants_count" INT NOT NULL  DEFAULT 0,
    "location_id" INT NOT NULL REFERENCES "locations" ("id") ON DELETE CASCADE,
    "organizer_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS "idx_events_title_44f4d6" ON "events" ("title");
CREATE INDEX IF NOT EXISTS "idx_events_date_8f5b3b" ON "events" ("date");
CREATE INDEX IF NOT EXISTS "idx_events_date_059eb2" ON "events" ("date", "time");
CREATE INDEX IF NOT EXISTS "idx_events_likes_c_87830d" ON "events" ("likes_count");
CREATE INDEX IF NOT EXISTS "idx_events_partici_d3f11e" ON "events" ("participants_count");
CREATE TABLE IF NOT EXISTS "event_categories" (
    "events_id" INT NOT NULL REFERENCES "events" ("id") ON DELETE CASCADE,
    "category_id" INT NOT NULL REFERENCES "categories" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "user_event_registrations" (
    "event_id" INT NOT NULL REFERENCES "events" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "user_event_likes" (
    "event_id" INT NOT NULL REFERENCES "events" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """

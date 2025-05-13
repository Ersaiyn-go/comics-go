-- =============== USERS TABLE ===============
CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(150) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user'
);


-- =============== COMICS TABLE ===============
CREATE TABLE IF NOT EXISTS comics (
    id SERIAL PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    description VARCHAR(500) NOT NULL,
    price FLOAT NOT NULL,
    image_url VARCHAR(300) NOT NULL,
    genre VARCHAR(50) DEFAULT 'Unknown',
    is_recommended BOOLEAN DEFAULT FALSE
);


-- =============== CART ITEM TABLE ===============
CREATE TABLE IF NOT EXISTS cart_item (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    comic_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE,
    FOREIGN KEY (comic_id) REFERENCES comics(id) ON DELETE CASCADE
);

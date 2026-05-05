-- 初始化PostgreSQL+PostGIS（需先安装PostGIS扩展）
CREATE EXTENSION IF NOT EXISTS postgis;

-- init.sql（手动创建用户表，可选）
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    hashed_password VARCHAR(100) NOT NULL,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
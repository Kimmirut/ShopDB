CREATE DATABASE shop_db;
CREATE USER 'user'@'localhost' IDENTIFIED BY 'password';

GRANT ALL PRIVILEGES ON shop_db.* TO 'user'@'localhost';
FLUSH PRIVILEGES;

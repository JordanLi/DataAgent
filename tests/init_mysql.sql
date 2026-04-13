CREATE DATABASE IF NOT EXISTS ecommerce;
USE ecommerce;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) COMMENT='User Accounts Table';

CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    category VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) COMMENT='Products Catalog';

CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    status INT NOT NULL COMMENT '1=Pending, 2=Paid, 3=Shipped, 4=Completed, 5=Cancelled',
    amount DECIMAL(10, 2) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) COMMENT='Orders Table';

-- Insert dummy data
INSERT INTO users (username, email) VALUES 
('alice', 'alice@example.com'),
('bob', 'bob@example.com'),
('charlie', 'charlie@example.com');

INSERT INTO products (name, price, category) VALUES 
('Laptop', 999.99, 'Electronics'),
('Phone', 699.50, 'Electronics'),
('Desk', 150.00, 'Furniture'),
('Chair', 85.00, 'Furniture');

INSERT INTO orders (user_id, status, amount) VALUES 
(1, 4, 999.99),
(1, 4, 150.00),
(2, 2, 699.50),
(3, 1, 85.00);

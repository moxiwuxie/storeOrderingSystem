-- =============================================================
-- 门店扫码点单系统 · MySQL 表结构（MySQL 8.0，字符集 utf8mb4）
-- 说明：本地开发默认使用 SQLite，由 ORM 自动建表；
--       生产环境建议使用 MySQL，执行本脚本初始化表结构。
-- 执行： mysql -u root -p < sql/mysql_schema.sql
-- =============================================================
CREATE DATABASE IF NOT EXISTS `store_ordering`
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `store_ordering`;

-- -------------------------------------------------------------
-- 用户表：微信 openid 与支付宝 user_id 两种身份
-- -------------------------------------------------------------
DROP TABLE IF EXISTS `order_items`;
DROP TABLE IF EXISTS `orders`;
DROP TABLE IF EXISTS `cart_items`;
DROP TABLE IF EXISTS `product_specs`;
DROP TABLE IF EXISTS `products`;
DROP TABLE IF EXISTS `categories`;
DROP TABLE IF EXISTS `admins`;
DROP TABLE IF EXISTS `users`;

CREATE TABLE `users` (
  `id`             BIGINT       NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `openid`         VARCHAR(64)  DEFAULT NULL COMMENT '微信 openid',
  `alipay_user_id` VARCHAR(64)  DEFAULT NULL COMMENT '支付宝 user_id',
  `device_id`      VARCHAR(64)  DEFAULT NULL COMMENT 'H5（浏览器/支付宝内打开）设备标识',
  `nickname`       VARCHAR(64)  NOT NULL DEFAULT '微信用户' COMMENT '昵称',
  `avatar`         VARCHAR(512) NOT NULL DEFAULT '' COMMENT '头像地址',
  `phone`          VARCHAR(20)  NOT NULL DEFAULT '' COMMENT '手机号',
  `status`         TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '1正常 0禁用',
  `created_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_users_openid` (`openid`),
  UNIQUE KEY `uk_users_alipay` (`alipay_user_id`),
  UNIQUE KEY `uk_users_device` (`device_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- -------------------------------------------------------------
-- 后台管理员表
-- -------------------------------------------------------------
CREATE TABLE `admins` (
  `id`            BIGINT       NOT NULL AUTO_INCREMENT,
  `username`      VARCHAR(64)  NOT NULL COMMENT '登录名',
  `password_hash` VARCHAR(255) NOT NULL COMMENT 'PBKDF2 哈希',
  `real_name`     VARCHAR(64)  NOT NULL DEFAULT '管理员',
  `status`        TINYINT(1)   NOT NULL DEFAULT 1,
  `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_admins_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='后台管理员表';

-- -------------------------------------------------------------
-- 商品分类表
-- -------------------------------------------------------------
CREATE TABLE `categories` (
  `id`         BIGINT      NOT NULL AUTO_INCREMENT,
  `name`       VARCHAR(64) NOT NULL COMMENT '分类名称',
  `sort`       INT         NOT NULL DEFAULT 0 COMMENT '排序，越小越靠前',
  `status`     TINYINT(1)  NOT NULL DEFAULT 1 COMMENT '1启用 0停用',
  `created_at` DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_categories_sort` (`sort`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品分类表';

-- -------------------------------------------------------------
-- 商品表（无规格商品使用 price/stock）
-- -------------------------------------------------------------
CREATE TABLE `products` (
  `id`          BIGINT        NOT NULL AUTO_INCREMENT,
  `category_id` BIGINT        NOT NULL COMMENT '所属分类',
  `name`        VARCHAR(128)  NOT NULL COMMENT '商品名称',
  `description` TEXT          COMMENT '商品简介',
  `image`       VARCHAR(512)  NOT NULL DEFAULT '' COMMENT '图片地址',
  `price`       DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '售价（无规格时生效）',
  `stock`       INT           NOT NULL DEFAULT 0 COMMENT '库存（无规格时生效）',
  `unit`        VARCHAR(16)   NOT NULL DEFAULT '份' COMMENT '单位',
  `sort`        INT           NOT NULL DEFAULT 0,
  `status`      TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '1上架 0下架',
  `created_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_products_category` (`category_id`),
  KEY `idx_products_status` (`status`),
  CONSTRAINT `fk_products_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品表';

-- -------------------------------------------------------------
-- 商品规格表（多规格：大杯/中杯、加辣等，价格与库存独立）
-- -------------------------------------------------------------
CREATE TABLE `product_specs` (
  `id`         BIGINT        NOT NULL AUTO_INCREMENT,
  `product_id` BIGINT        NOT NULL,
  `name`       VARCHAR(64)   NOT NULL COMMENT '规格名',
  `price`      DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `stock`      INT           NOT NULL DEFAULT 0,
  `sort`       INT           NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_specs_product` (`product_id`),
  UNIQUE KEY `uk_specs_product_name` (`product_id`, `name`),
  CONSTRAINT `fk_specs_product` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品规格表';

-- -------------------------------------------------------------
-- 购物车表（user + product + spec 唯一）
-- -------------------------------------------------------------
CREATE TABLE `cart_items` (
  `id`         BIGINT   NOT NULL AUTO_INCREMENT,
  `user_id`    BIGINT   NOT NULL,
  `product_id` BIGINT   NOT NULL,
  `spec_id`    BIGINT   DEFAULT NULL COMMENT '为空表示无规格商品',
  `quantity`   INT      NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_cart_item` (`user_id`, `product_id`, `spec_id`),
  KEY `idx_cart_user` (`user_id`),
  CONSTRAINT `fk_cart_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_cart_product` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='购物车表';

-- -------------------------------------------------------------
-- 订单主表
-- status: 0待支付 1已支付 2已完成 3已取消
-- -------------------------------------------------------------
CREATE TABLE `orders` (
  `id`             BIGINT        NOT NULL AUTO_INCREMENT,
  `order_no`       VARCHAR(40)   NOT NULL COMMENT '订单编号 SO+时间+随机数',
  `user_id`        BIGINT        NOT NULL,
  `total_amount`   DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '订单总额',
  `pay_amount`     DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '实付金额',
  `status`         TINYINT       NOT NULL DEFAULT 0 COMMENT '0待支付 1已支付 2已完成 3已取消',
  `pay_type`       VARCHAR(16)   NOT NULL DEFAULT '' COMMENT 'wechat/alipay',
  `transaction_id` VARCHAR(64)   NOT NULL DEFAULT '' COMMENT '渠道交易号',
  `table_no`       VARCHAR(32)   NOT NULL DEFAULT '' COMMENT '桌号',
  `remark`         VARCHAR(255)  NOT NULL DEFAULT '' COMMENT '备注',
  `pay_time`       DATETIME      DEFAULT NULL,
  `created_at`     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_orders_no` (`order_no`),
  KEY `idx_orders_user` (`user_id`),
  KEY `idx_orders_status` (`status`),
  KEY `idx_orders_created` (`created_at`),
  CONSTRAINT `fk_orders_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单主表';

-- -------------------------------------------------------------
-- 订单明细表（记录下单时的商品快照）
-- -------------------------------------------------------------
CREATE TABLE `order_items` (
  `id`            BIGINT        NOT NULL AUTO_INCREMENT,
  `order_id`      BIGINT        NOT NULL,
  `product_id`    BIGINT        NOT NULL,
  `product_name`  VARCHAR(128)  NOT NULL COMMENT '商品名快照',
  `product_image` VARCHAR(512)  NOT NULL DEFAULT '',
  `spec_id`       BIGINT        DEFAULT NULL,
  `spec_name`     VARCHAR(64)   NOT NULL DEFAULT '' COMMENT '规格名快照',
  `price`         DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '成交单价',
  `quantity`      INT           NOT NULL DEFAULT 1,
  `subtotal`      DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  PRIMARY KEY (`id`),
  KEY `idx_items_order` (`order_id`),
  KEY `idx_items_product` (`product_id`),
  CONSTRAINT `fk_items_order` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单明细表';

-- -------------------------------------------------------------
-- 初始化数据：默认管理员（密码 admin123，上线后请立即修改）
-- 哈希由后端 security.hash_password 生成，建议首次启动由后端自动写入
-- -------------------------------------------------------------
-- INSERT INTO `admins` (`username`, `password_hash`) VALUES ('admin', '<PBKDF2_HASH>');

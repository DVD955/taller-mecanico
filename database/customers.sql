-- UC-CV-01. Migración aditiva: conserva usuarios y sesiones existentes.
CREATE TABLE IF NOT EXISTS customers (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(120) NOT NULL,
  street VARCHAR(150) NOT NULL,
  number VARCHAR(20) NOT NULL,
  neighborhood VARCHAR(100) NOT NULL,
  municipality VARCHAR(100) NOT NULL,
  state VARCHAR(100) NOT NULL,
  email VARCHAR(254) NULL,
  mobile VARCHAR(16) NULL,
  alternative VARCHAR(16) NULL,
  status ENUM('ACTIVO','INACTIVO') NOT NULL DEFAULT 'ACTIVO',
  identity_fingerprint CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
  created_at DATETIME(6) NOT NULL,
  version INT NOT NULL DEFAULT 1,
  deleted_at DATETIME(6) NULL COMMENT 'UTC: baja lógica; conserva auditoría',
  CONSTRAINT chk_customer_contact CHECK (email IS NOT NULL OR mobile IS NOT NULL OR alternative IS NOT NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Teléfonos se comparten entre celular y alternativo: misma clave PHONE.
CREATE TABLE IF NOT EXISTS customer_contact_keys (
  kind VARCHAR(10) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  value VARCHAR(254) COLLATE utf8mb4_bin NOT NULL,
  customer_id BIGINT NOT NULL,
  PRIMARY KEY (kind, value),
  CONSTRAINT fk_contact_customer FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS audit_entries (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  actor_id INT NOT NULL,
  actor_username VARCHAR(50) NOT NULL,
  customer_id BIGINT NOT NULL,
  action VARCHAR(80) NOT NULL,
  occurred_at DATETIME(6) NOT NULL COMMENT 'UTC',
  CONSTRAINT fk_audit_customer FOREIGN KEY (customer_id) REFERENCES customers(id),
  INDEX idx_audit_customer_time (customer_id, occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

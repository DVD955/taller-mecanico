-- UC-CV-01. Estatus normalizado en el catálogo; conserva usuarios y sesiones.
CREATE TABLE IF NOT EXISTS status (
  id INT PRIMARY KEY,
  valor VARCHAR(20) NOT NULL UNIQUE,
  descripcion VARCHAR(150) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO status (id,valor,descripcion) VALUES
  (1,'activo','Usuario o registro activo'),
  (2,'suspendido','Usuario o registro suspendido; se conserva'),
  (3,'eliminado','Registro dado de baja lógica; se conserva');
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
  bin_status INT NOT NULL DEFAULT 1,
  identity_fingerprint CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
  created_at DATETIME(6) NOT NULL,
  version INT NOT NULL DEFAULT 1,
  deleted_at DATETIME(6) NULL COMMENT 'UTC: baja lógica; conserva auditoría',
  workshop_id INT NULL COMMENT 'Obligatorio en altas nuevas; inmutable; NULL solo en registros anteriores',
  CONSTRAINT chk_customer_contact CHECK (email IS NOT NULL OR mobile IS NOT NULL OR alternative IS NOT NULL),
  CONSTRAINT fk_customers_bin_status FOREIGN KEY (bin_status) REFERENCES status(id),
  CONSTRAINT fk_customers_workshop FOREIGN KEY (workshop_id) REFERENCES workshops(id)
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

-- UC-CV-06: cliente obligatorio; en esta fase no se asigna técnico.
CREATE TABLE IF NOT EXISTS vehicles (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  customer_id BIGINT NOT NULL,
  vin CHAR(17) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
  plate VARCHAR(10) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
  make VARCHAR(60) NOT NULL,
  model VARCHAR(60) NOT NULL,
  year INT NOT NULL,
  version VARCHAR(60) NOT NULL,
  color VARCHAR(40) NOT NULL,
  mileage INT NULL,
  bin_status INT NOT NULL DEFAULT 1,
  record_version INT NOT NULL DEFAULT 1,
  updated_at DATETIME(6) NULL,
  deleted_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL,
  CONSTRAINT fk_vehicle_customer FOREIGN KEY (customer_id) REFERENCES customers(id),
  CONSTRAINT fk_vehicle_status FOREIGN KEY (bin_status) REFERENCES status(id),
  CONSTRAINT chk_vehicle_mileage CHECK (mileage IS NULL OR mileage BETWEEN 0 AND 10000000),
  INDEX idx_vehicle_customer (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS vehicle_audit_entries (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  actor_id INT NOT NULL,
  actor_username VARCHAR(50) NOT NULL,
  customer_id BIGINT NOT NULL,
  vehicle_id BIGINT NOT NULL,
  action VARCHAR(80) NOT NULL,
  previous_customer_id BIGINT NULL,
  occurred_at DATETIME(6) NOT NULL COMMENT 'UTC',
  CONSTRAINT fk_vehicle_audit_customer FOREIGN KEY (customer_id) REFERENCES customers(id),
  CONSTRAINT fk_vehicle_audit_vehicle FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
  INDEX idx_vehicle_audit_time (vehicle_id,occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Fotografías privadas: nunca se publican como archivos estáticos.
CREATE TABLE IF NOT EXISTS vehicle_photos (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  vehicle_id BIGINT NOT NULL,
  content_type VARCHAR(20) NOT NULL,
  size_bytes INT NOT NULL,
  content MEDIUMBLOB NOT NULL,
  created_at DATETIME(6) NOT NULL,
  CONSTRAINT fk_vehicle_photo FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
  CONSTRAINT chk_vehicle_photo_size CHECK (size_bytes BETWEEN 1 AND 15000000),
  INDEX idx_vehicle_photo (vehicle_id,id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

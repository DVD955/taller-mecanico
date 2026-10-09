CREATE DATABASE IF NOT EXISTS taller_mecanico
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE taller_mecanico;

CREATE TABLE IF NOT EXISTS status (
  id INT PRIMARY KEY,
  valor VARCHAR(20) NOT NULL UNIQUE,
  descripcion VARCHAR(150) NOT NULL
) ENGINE=InnoDB;
INSERT IGNORE INTO status (id,valor,descripcion) VALUES
  (1,'activo','Usuario o registro activo'),
  (2,'suspendido','Usuario o registro suspendido; se conserva'),
  (3,'eliminado','Registro dado de baja lógica; se conserva');
UPDATE status SET valor='suspendido', descripcion='Usuario o registro suspendido; se conserva'
WHERE id=2 AND valor='inactivo';

CREATE TABLE IF NOT EXISTS roles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(50) NOT NULL UNIQUE,
  name VARCHAR(50) NOT NULL UNIQUE,
  description VARCHAR(200) NOT NULL,
  bin_status INT NOT NULL DEFAULT 1,
  version INT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (bin_status) REFERENCES status(id)
) ENGINE=InnoDB;
INSERT IGNORE INTO roles (code,name,description) VALUES
  ('ADMINISTRADOR','Administrador','Administra roles, cuentas, clientes y talleres'),
  ('RECEPCIONISTA','Recepcionista','Registra y administra clientes y talleres'),
  ('MECANICO','Mecánico','Cuenta de personal'),
  ('INVITADO','Invitado','Cuenta del registro público');

CREATE TABLE IF NOT EXISTS users (
  id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(120) NOT NULL,
  email VARCHAR(255) NULL UNIQUE,
  role VARCHAR(50) NOT NULL DEFAULT 'INVITADO',
  bin_status INT NOT NULL DEFAULT 1,
  recovery_code_hash VARCHAR(255) NULL,
  recovery_expires_at DATETIME NULL,
  active_session_id CHAR(36) NULL UNIQUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_users_username (username),
  FOREIGN KEY (role) REFERENCES roles(code),
  FOREIGN KEY (bin_status) REFERENCES status(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS user_sessions (
  id CHAR(36) PRIMARY KEY,
  user_id INT UNSIGNED NOT NULL,
  started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at DATETIME NOT NULL,
  ended_at DATETIME NULL,
  CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_sessions_user (user_id),
  INDEX idx_sessions_active (id, ended_at, expires_at)
) ENGINE=InnoDB;

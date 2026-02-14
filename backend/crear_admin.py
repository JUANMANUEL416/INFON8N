#!/usr/bin/env python3
"""Script para crear usuario administrador"""

import bcrypt
import psycopg2
import os

# Configuración de la base de datos
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'informes_db'),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASSWORD', 'admin123')
}

try:
    # Conectar a la base de datos
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    
    # Hash de la contraseña
    password = 'admin123'
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Insertar usuario admin
    cur.execute('''
        INSERT INTO usuarios (username, nombre, password_hash, role)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (username) DO UPDATE
        SET password_hash = EXCLUDED.password_hash,
            nombre = EXCLUDED.nombre,
            role = EXCLUDED.role
    ''', ('admin', 'Administrador', password_hash, 'admin'))
    
    conn.commit()
    print("✓ Usuario 'admin' creado/actualizado correctamente")
    print("  Username: admin")
    print("  Password: admin123")
    print("  Role: admin")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)

#!/usr/bin/env python3
"""
Script de inicio: crea tablas y pobla la base de datos, luego lanza la app.
Úsalo para desarrollo local: python run.py
"""
from app import app, db, seed_db

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_db()
        print("✅ Base de datos lista")
    print("🎬 Iniciando CINEMAX en http://localhost:5000")
    app.run(debug=True, port=5000)

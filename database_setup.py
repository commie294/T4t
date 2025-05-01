import sqlite3

DATABASE_NAME = 't4t_meet.db'

def create_tables():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            bio TEXT,
            photo_id TEXT NOT NULL,
            is_adult BOOLEAN DEFAULT FALSE,
            age_preference TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id_1 INTEGER NOT NULL,
            user_id_2 INTEGER NOT NULL,
            is_match BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id_1) REFERENCES users(user_id),
            FOREIGN KEY (user_id_2) REFERENCES users(user_id),
            UNIQUE(user_id_1, user_id_2)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_user_id INTEGER NOT NULL,
            reported_user_id INTEGER NOT NULL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (reporter_user_id) REFERENCES users(user_id),
            FOREIGN KEY (reported_user_id) REFERENCES users(user_id),
            UNIQUE(reporter_user_id, reported_user_id)
        )
    """)

    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'is_adult' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN is_adult BOOLEAN DEFAULT FALSE")
    
    if 'age_preference' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN age_preference TEXT")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_tables()
    print(f"Таблицы 'users', 'matches' и 'reports' успешно созданы (или уже существовали) в файле '{DATABASE_NAME}'.")

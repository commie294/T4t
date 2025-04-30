import sqlite3

DATABASE_NAME = 't4t_meet.db'

def create_tables():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Создание таблицы users
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            bio TEXT,
            interests TEXT,
            seeking_gender TEXT,
            seeking_age_min INTEGER,
            seeking_age_max INTEGER,
            photo_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Создание таблицы matches
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id_1 INTEGER NOT NULL,
            user_id_2 INTEGER NOT NULL,
            is_match BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id_1) REFERENCES users(user_id),
            FOREIGN KEY (user_id_2) REFERENCES users(user_id)
        )
    """)

    # Создание таблицы reports
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_user_id INTEGER NOT NULL,
            reported_user_id INTEGER NOT NULL,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (reporter_user_id) REFERENCES users(user_id),
            FOREIGN KEY (reported_user_id) REFERENCES users(user_id)
        )
    """)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_tables()
    print(f"Таблицы 'users', 'matches' и 'reports' успешно созданы (или уже существовали) в файле '{DATABASE_NAME}'.")

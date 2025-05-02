import sqlite3

DATABASE_NAME = 't4t_meet.db'

def create_tables():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Таблица пользователей
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
            city TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_blocked BOOLEAN DEFAULT FALSE,
            block_reason TEXT
        )
    """)

    # Таблица мэтчей
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

    # Таблица жалоб
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_user_id INTEGER NOT NULL,
            reported_user_id INTEGER NOT NULL,
            reason TEXT,
            admin_action TEXT,
            admin_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (reporter_user_id) REFERENCES users(user_id),
            FOREIGN KEY (reported_user_id) REFERENCES users(user_id))
    """)

    # Таблица просмотренных профилей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS viewed_profiles (
            viewer_id INTEGER NOT NULL,
            viewed_id INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (viewer_id) REFERENCES users(user_id),
            FOREIGN KEY (viewed_id) REFERENCES users(user_id),
            PRIMARY KEY (viewer_id, viewed_id)
        )
    """)

    # Таблица действий администраторов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            reason TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id))
    """)

    # Индексы для ускорения запросов
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_blocked ON users(is_blocked)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_reported ON reports(reported_user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_matches_users ON matches(user_id_1, user_id_2)")

    conn.commit()
    conn.close()

def migrate_database():
    """Миграция существующей базы данных"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    try:
        # Проверяем существующие столбцы
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Добавляем недостающие столбцы
        if 'is_blocked' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN is_blocked BOOLEAN DEFAULT FALSE")
        if 'block_reason' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN block_reason TEXT")
        
        # Создаем таблицу admin_actions если ее нет
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='admin_actions'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE admin_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    reason TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id))
            """)
        
        conn.commit()
        print("Миграция базы данных успешно завершена")
    except Exception as e:
        print(f"Ошибка при миграции базы данных: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    create_tables()
    migrate_database()
    print(f"База данных '{DATABASE_NAME}' успешно инициализирована")

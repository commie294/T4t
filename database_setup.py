import sqlite3
from typing import Optional

DATABASE_NAME = 't4t_meet.db'

def main():
    initialize_database()  # Эта функция теперь будет из database_setup.py
    # Дальнейшая инициализация бота
def check_index_exists(cursor: sqlite3.Cursor, index_name: str) -> bool:
    """Проверяет существование индекса в базе данных"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name=?", (index_name,))
    return cursor.fetchone() is not None

def create_tables():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    try:
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
                block_reason TEXT,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                FOREIGN KEY (user_id_1) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id_2) REFERENCES users(user_id) ON DELETE CASCADE,
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
                FOREIGN KEY (reporter_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (reported_user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)

        # Таблица просмотренных профилей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS viewed_profiles (
                viewer_id INTEGER NOT NULL,
                viewed_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (viewer_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (viewed_id) REFERENCES users(user_id) ON DELETE CASCADE,
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
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)

        # Создаем индексы, если они не существуют
        indexes = [
            ("idx_users_blocked", "users(is_blocked)"),
            ("idx_users_city", "users(city)"),
            ("idx_users_age", "users(age)"),
            ("idx_users_gender", "users(gender)"),
            ("idx_reports_reported", "reports(reported_user_id)"),
            ("idx_matches_users", "matches(user_id_1, user_id_2)"),
            ("idx_viewed_profiles", "viewed_profiles(viewer_id, viewed_id)"),
            ("idx_users_last_active", "users(last_active)")
        ]

        for index_name, index_columns in indexes:
            if not check_index_exists(cursor, index_name):
                cursor.execute(f"CREATE INDEX {index_name} ON {index_columns}")

        conn.commit()
        print("Таблицы и индексы успешно созданы")
    except Exception as e:
        conn.rollback()
        print(f"Ошибка при создании таблиц: {e}")
        raise
    finally:
        conn.close()

def migrate_database():
    """Миграция существующей базы данных"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    try:
        # Проверяем существующие столбцы в таблице users
        cursor.execute("PRAGMA table_info(users)")
        columns = {column[1]: column for column in cursor.fetchall()}
        
        # Добавляем недостающие столбцы
        if 'is_blocked' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN is_blocked BOOLEAN DEFAULT FALSE")
        if 'block_reason' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN block_reason TEXT")
        if 'last_active' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        
        # Создаем таблицу admin_actions если ее нет
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_actions'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE admin_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    reason TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
        
        # Добавляем ON DELETE CASCADE для существующих таблиц
        tables = ['matches', 'reports', 'viewed_profiles']
        for table in tables:
            cursor.execute(f"PRAGMA foreign_key_list({table})")
            if not cursor.fetchall():  # Если нет ограничений внешнего ключа
                # SQLite не поддерживает изменение ограничений, нужно создать новую таблицу и перенести данные
                print(f"Обновление ограничений для таблицы {table} не поддерживается напрямую, требуется ручная миграция")
        
        conn.commit()
        print("Миграция базы данных успешно завершена")
    except Exception as e:
        conn.rollback()
        print(f"Ошибка при миграции базы данных: {e}")
        raise
    finally:
        conn.close()

def check_database_integrity() -> bool:
    """Проверяет целостность базы данных"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        return result[0] == 'ok'
    except Exception as e:
        print(f"Ошибка при проверке целостности базы данных: {e}")
        return False
    finally:
        conn.close()

def backup_database(backup_path: str) -> bool:
    """Создает резервную копию базы данных"""
    try:
        import shutil
        shutil.copy2(DATABASE_NAME, backup_path)
        print(f"Резервная копия создана: {backup_path}")
        return True
    except Exception as e:
        print(f"Ошибка при создании резервной копии: {e}")
        return False

if __name__ == "__main__":
    print("Инициализация базы данных T4T Meet")
    
    try:
        create_tables()
        migrate_database()
        
        if check_database_integrity():
            print(f"База данных '{DATABASE_NAME}' успешно инициализирована и проверена")
        else:
            print("Обнаружены проблемы с целостностью базы данных")
            
        # Создаем резервную копию
        backup_database(f"{DATABASE_NAME}.backup")
    except Exception as e:
        print(f"Ошибка при инициализации базы данных: {e}")

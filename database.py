
import sqlite3

from pathlib import Path


# Find the folder where this Python file is located.
BASE_DIR = Path(__file__).resolve().parent

# Store the database inside the project folder.
DATABASE_PATH = BASE_DIR / "daily_work_log.db"


def get_connection():
    """Open a connection to the SQLite database."""
    connection = sqlite3.connect(DATABASE_PATH)

    # Return database rows that can be accessed by column name.
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    """Create the activities table if it does not exist."""
    connection = get_connection()

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_date TEXT NOT NULL,
                activity_time TEXT,
                title TEXT NOT NULL,
                notes TEXT,
                priority TEXT NOT NULL DEFAULT 'Medium'
                    CHECK (priority IN ('Low', 'Medium', 'High')),
                status TEXT NOT NULL DEFAULT 'Pending'
                    CHECK (status IN (
                        'Pending', 'In Progress', 'Completed'
                    )),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.commit()

    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully.")
    print(f"Database location: {DATABASE_PATH}")

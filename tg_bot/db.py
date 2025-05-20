import sqlite3


class Database:
    def __init__(self, db_file):
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()

    def user_exists(self, user_id):
        """
        Check if user exists in database
        """
        with self.connection:
            result = self.cursor.execute(
                f'SELECT * FROM users WHERE user_id = {user_id};').fetchmany(1)
            return bool(len(result))

    def add_user(self, user_id):
        """
        Add new user in database
        """
        with self.connection:
            return self.cursor.execute(f'INSERT INTO users (user_id) VALUES ({user_id});')

    def set_active(self, user_id, active):
        with self.connection:
            return self.cursor.execute(f'UPDATE users SET active = {active} WHERE user_id = {user_id}')

    def get_all_users(self):
        with self.connection:
            return self.cursor.execute(f'SELECT user_id, active FROM users').fetchall()

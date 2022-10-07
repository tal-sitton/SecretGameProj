import sqlite3

db_path = r"SQL\database.db"
table = "players"


class SQLHandler:
    def __init__(self):
        self.db = create_connection(db_path)
        if not self.db:
            print("SOMETHINGS WRONG!!!")
        else:
            self.cursor = self.db.cursor()
            self.table = table

    def get_data(self, col="*", filter_tuple=(None, None)) -> list:
        """
        gets data from the sql
        :param col: the column to get the data from
        :param filter_tuple: (column name, column value)
        :return: the data from the specified column
        """
        if filter_tuple == (None, None):
            self.cursor.execute(f"SELECT {col} FROM {self.table}")
            result = self.cursor.fetchall()
            return result
        else:
            sql = f"SELECT {col} FROM {self.table} WHERE {filter_tuple[0]} ='{filter_tuple[1]}'"
            self.cursor.execute(sql)
            result = self.cursor.fetchall()
            return result

    def update(self, col, new_value, filter_column, filter_value):
        """
        updates value in the db
        :param col: the column for the data to update
        :param new_value: the new value of the column
        :param filter_column: the column to check the value of
        :param filter_value: the value the filter_column should be
        """
        sql = f"UPDATE {self.table} SET {col} = ? WHERE {filter_column} = ?"
        val = (new_value, filter_value)
        self.cursor.execute(sql, val)
        self.db.commit()

    def update_inc(self, col, filter_column, filter_value):
        """
        increases the value of a specified column
        :param col: the column for the data to update
        :param filter_column: the column to check the value of
        :param filter_value: the value the filter_column should be
        """
        sql = f"UPDATE {self.table} SET {col} = {col}+1 WHERE {filter_column} ={filter_value}"
        self.cursor.execute(sql)
        self.db.commit()

    def insert(self, username, password, json_data) -> int:
        sql = f"INSERT INTO {self.table}(username,password,json_data) VALUES(?,?,?,?)"
        val = (username, password, json_data)
        self.cursor.execute(sql, val)
        self.db.commit()

        self.cursor.execute(f"select * from {self.table}")
        rowcount = len(self.cursor.fetchall())
        print(rowcount, "record inserted.")

        return rowcount

    def create_table(self, name):
        self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {name} (username text, "
                            "password BINARY(32),json_data text)")


def create_connection(db_file):
    """ create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print("version:", sqlite3.version)
    except Exception as e:
        print(e)
    return conn

import json
import sqlite3

db_path = r"SQL/database.db"
table = "data"

default_data = json.dumps({"user_scores": {}, "prog_scores": {}, "got_peoples_score": [],
                           "games": ["The Legend of Zelda: Ocarina of Time", "Tony Hawk's Pro Skater 2",
                                     "Grand Theft Auto IV",
                                     "SoulCalibur", "Super Mario Galaxy", "Super Mario Galaxy 2",
                                     "Red Dead Redemption 2",
                                     "Grand Theft Auto V", "Disco Elysium: The Final Cut",
                                     "The Legend of Zelda: Breath of the Wild", "Tony Hawk's Pro Skater 3",
                                     "Perfect Dark",
                                     "Metroid Prime", "Grand Theft Auto III", "Super Mario Odyssey",
                                     "Halo: Combat Evolved",
                                     "NFL 2K1", "Half-Life 2", "BioShock", "GoldenEye 007",
                                     "Uncharted 2: Among Thieves",
                                     "Resident Evil 4", "The Orange Box", "Batman: Arkham City", "Tekken 3",
                                     "Elden Ring",
                                     "Mass Effect 2", "The House in Fata Morgana - Dreams of the Revenants Edition -",
                                     "The Legend of Zelda: Twilight Princess", "The Elder Scrolls V: Skyrim",
                                     "Half-Life",
                                     "The Legend of Zelda: The Wind Waker", "Gran Turismo",
                                     "Portal Companion Collection",
                                     "Metal Gear Solid 2: Sons of Liberty", "Grand Theft Auto Double Pack",
                                     "Baldur's Gate II: Shadows of Amn", "Grand Theft Auto: San Andreas",
                                     "Grand Theft Auto: Vice City", "LittleBigPlanet",
                                     "The Legend of Zelda Collector's Edition",
                                     "Red Dead Redemption", "Gran Turismo 3: A-Spec", "Halo 2",
                                     "The Legend of Zelda: A Link to the Past", "The Legend of Zelda: Majora's Mask",
                                     "The Last of Us", "Madden NFL 2003", "Persona 5 Royal",
                                     "The Last of Us Remastered",
                                     "Portal 2", "Metal Gear Solid V: The Phantom Pain", "Tetris Effect: Connected",
                                     "World of Goo", "BioShock Infinite", "Final Fantasy IX",
                                     "Call of Duty: Modern Warfare 2",
                                     "God of War", "Tony Hawk's Pro Skater 4", "Devil May Cry",
                                     "Call of Duty 4: Modern Warfare",
                                     "Madden NFL 2002", "The Legend of Zelda: Ocarina of Time 3D", "Chrono Cross",
                                     "Celeste",
                                     "Madden NFL 2004", "Gears of War", "The Elder Scrolls IV: Oblivion",
                                     "Sid Meier's Civilization II", "Quake", "Halo 3", "Ninja Gaiden Black",
                                     "Street Fighter IV"],
                           "calculated": False,
                           "calculating": False,
                           "prev_calc": 0})


class SQLHandler:
    def __init__(self):
        self.db = create_connection(db_path)
        if not self.db:
            print("SOMETHINGS WRONG!!!")
        else:
            self.cursor = self.db.cursor()
            self.table = table

    def get_data(self, col="*", filter_tuple=(None, None), t: type = None) -> list:
        """
        gets data from the sql
        :param col: the column to get the data from
        :param filter_tuple: (column name, column value)
        :return: the data from the specified column
        """
        if filter_tuple == (None, None):
            self.cursor.execute(f"SELECT {col} FROM {self.table}")
            result = self.cursor.fetchall()
        else:
            sql = f"SELECT {col} FROM {self.table} WHERE {filter_tuple[0]} ='{filter_tuple[1]}'"
            self.cursor.execute(sql)
            result = self.cursor.fetchall()
            if t:
                return [t(r[0]) for r in result]
        if "," not in col and col != "*":
            return [r[0] for r in result]
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

    def insert(self, username, password, json_data=default_data) -> int:
        sql = f"INSERT INTO {self.table}(username,password,json_data) VALUES(?,?,?)"
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


def startup():
    sql = SQLHandler()
    sql.create_table("data")


if __name__ == '__main__':
    startup()

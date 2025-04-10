from memory.database import Database

def init_db():
       db = Database("recruit_pro.db")
       db.create_tables()

if __name__ == "__main__":
       init_db()
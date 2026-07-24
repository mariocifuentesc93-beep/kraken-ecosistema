from database.database_manager import database_manager


def migrate():

    database_manager.initialize()

    print("[DATABASE] Base de datos creada correctamente.")


if __name__ == "__main__":
    migrate()

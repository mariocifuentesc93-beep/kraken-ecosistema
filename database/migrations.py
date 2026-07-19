from database.schema import create_tables


def migrate():

    create_tables()

    print("[DATABASE] Base de datos creada correctamente.")


if __name__ == "__main__":
    migrate()
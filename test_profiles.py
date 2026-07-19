from controllers.profile_controller import profile_controller

print("=" * 50)
print("PRUEBA DEL CRUD DE PERFILES")
print("=" * 50)

# Crear
print("\n[1] Creando perfil...")

profile = profile_controller.create(
    name="FTMO Scalping",
    description="Perfil principal",
)

print(f"OK -> {profile.name}")

# Listar
print("\n[2] Listando perfiles...")

profiles = profile_controller.get_all()

for p in profiles:
    print(f"{p.id} | {p.name} | {p.execution_mode}")

# Duplicar
print("\n[3] Duplicando perfil...")

copy = profile_controller.duplicate(profile.id)

print(f"OK -> {copy.name}")

# Listar nuevamente
print("\n[4] Perfiles actuales...")

profiles = profile_controller.get_all()

for p in profiles:
    print(f"{p.id} | {p.name}")

# Eliminar la copia
print("\n[5] Eliminando copia...")

profile_controller.delete(copy.id)

print("Copia eliminada.")

# Listado final
print("\n[6] Resultado final...")

profiles = profile_controller.get_all()

for p in profiles:
    print(f"{p.id} | {p.name}")

print("\nCRUD FINALIZADO CORRECTAMENTE")
from app.models import Base, User, Customer, Microgrid, Device, Load


def test_models_import_successfully():
    assert User.__tablename__ == "users"
    assert Customer.__tablename__ == "customers"
    assert Microgrid.__tablename__ == "microgrids"
    assert Device.__tablename__ == "devices"
    assert Load.__tablename__ == "loads"


def test_metadata_contains_all_foundational_tables():
    table_names = set(Base.metadata.tables.keys())
    assert {"users", "customers", "microgrids", "devices", "loads"}.issubset(table_names)

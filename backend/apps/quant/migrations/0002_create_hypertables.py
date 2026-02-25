from django.db import connection, migrations


def create_hypertables(apps, schema_editor):
    """Create TimescaleDB hypertables. Only runs on PostgreSQL."""
    if connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT create_hypertable('quant_klinedata', 'date', "
            "if_not_exists => TRUE, migrate_data => TRUE);"
        )
        cursor.execute(
            "SELECT create_hypertable('quant_moneyflow', 'date', "
            "if_not_exists => TRUE, migrate_data => TRUE);"
        )
        cursor.execute(
            "SELECT create_hypertable('quant_margindata', 'date', "
            "if_not_exists => TRUE, migrate_data => TRUE);"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("quant", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            create_hypertables,
            reverse_code=migrations.RunPython.noop,
        ),
    ]

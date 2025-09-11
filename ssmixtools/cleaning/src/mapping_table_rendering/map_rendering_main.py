from .code_to_code_map_rendering import (
    create_hot7_to_yj7_table,
    create_mdcdx2_to_icd10_table,
    create_hot7_to_atc_table,
    create_yj7_to_atc_table,
)
from .code_to_text_mapping import create_jlac10_to_text_tables
from .text_to_code_mapping import create_text_to_yj7_table, create_text_to_atc_table
from .table_render_utils import (
    load_dx_tables,
    load_hot_tables,
    load_atc_tables,
)


def render_mapping_tables(output_dir: str, atc_tables_dir: str):
    """Renders code maps needed for data cleaning."""
    # ================
    # Load base tables
    # ================
    print("Loading ICD-10 tables...")
    medis_dx_tables = load_dx_tables()
    print("Loading HOT tables...")
    medis_hot_tables = load_hot_tables()
    print("Loading ATC tables...")
    atc_tables = load_atc_tables(atc_tables_dir=atc_tables_dir)

    # ==================
    # Render maps & save
    # ==================
    print("Rendering table to map MDCDX2 to ICD-10...")
    # create_mdcdx2_to_icd10_table(output_dir=output_dir, medis_dx_tables=medis_dx_tables)
    print("Rendering tables to map JLAC10...")
    # create_jlac10_to_text_tables(output_dir=output_dir)
    print("Rendering table to map HOT7 to YJ7...")
    create_hot7_to_yj7_table(output_dir=output_dir, medis_hot_tables=medis_hot_tables)
    if atc_tables_dir is not None:
        print("Rendering table to map drug names to YJ7...")
        create_text_to_yj7_table(
            output_dir=output_dir,
            atc_tables=atc_tables,
            medis_hot_tables=medis_hot_tables,
        )
        print("Rendering table to map YJ7 to ATC...")
        create_yj7_to_atc_table(output_dir=output_dir, atc_tables=atc_tables)
        print("Rendering table to map HOT7 to ATC...")
        create_hot7_to_atc_table(output_dir=output_dir, atc_tables=atc_tables)
        print("Rendering table to map drug names to ATC...")
        create_text_to_atc_table(output_dir=output_dir, atc_tables=atc_tables)

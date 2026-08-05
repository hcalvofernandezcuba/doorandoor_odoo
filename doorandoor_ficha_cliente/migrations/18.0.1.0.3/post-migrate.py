def migrate(cr, version):
    cr.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'sale_order'
            )
            AND NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'sale_order'
                  AND column_name = 'ddfc_pricing_source'
            ) THEN
                ALTER TABLE sale_order ADD COLUMN ddfc_pricing_source varchar;
            END IF;

            IF EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'account_move'
            )
            AND NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'account_move'
                  AND column_name = 'ddfc_pricing_source'
            ) THEN
                ALTER TABLE account_move ADD COLUMN ddfc_pricing_source varchar;
            END IF;

            IF EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'account_move'
            )
            AND NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'account_move'
                  AND column_name = 'ddfc_builder_id'
            ) THEN
                ALTER TABLE account_move ADD COLUMN ddfc_builder_id integer;
                ALTER TABLE account_move ADD CONSTRAINT account_move_ddfc_builder_id_fkey FOREIGN KEY (ddfc_builder_id) REFERENCES ddfc_builder_profile(id);
            END IF;
        END $$;

        UPDATE sale_order
        SET ddfc_pricing_source = CASE
            WHEN ddfc_builder_id IS NULL THEN 'base'
            ELSE 'constructor'
        END
        WHERE ddfc_pricing_source IS NULL OR ddfc_pricing_source = '';

        UPDATE account_move
        SET ddfc_pricing_source = CASE
            WHEN ddfc_builder_id IS NULL THEN 'base'
            ELSE 'constructor'
        END
        WHERE ddfc_pricing_source IS NULL OR ddfc_pricing_source = '';
    """)

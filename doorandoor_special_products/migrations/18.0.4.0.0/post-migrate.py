def migrate(cr, version):
    cr.execute(
        """
        UPDATE product_template
           SET ddsp_product_kind = 'transformed'
         WHERE ddsp_is_special = TRUE
           AND ddsp_product_kind IS NULL
        """
    )

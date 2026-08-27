def migrate(cr, version):
    cr.execute(
        """
        UPDATE product_template
           SET product_add_mode = 'configurator'
         WHERE product_add_mode IS DISTINCT FROM 'configurator'
        """
    )

def migrate(cr, version):
    """Allow the packaged manuals to receive their controlled new versions."""
    cr.execute(
        """
        UPDATE ir_model_data
           SET noupdate = FALSE
         WHERE module = 'doorandoor_operational_manuals'
           AND name IN (
               'manual_historic_logistics',
               'manual_initial_inventory',
               'manual_warehouse_operations'
           )
        """
    )

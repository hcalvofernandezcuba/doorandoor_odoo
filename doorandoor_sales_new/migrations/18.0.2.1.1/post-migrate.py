def migrate(cr, version):
    """Ensure the hourly preinvoice cleanup/reservation cron is enabled."""
    cr.execute(
        """
        UPDATE ir_cron
           SET active = TRUE
         WHERE id = (
             SELECT res_id
               FROM ir_model_data
              WHERE module = 'doorandoor_sales_new'
                AND name = 'ir_cron_ddsn_release_expired_quote_reservations'
                AND model = 'ir.cron'
              LIMIT 1
         )
        """
    )

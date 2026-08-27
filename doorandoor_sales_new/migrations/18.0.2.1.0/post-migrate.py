def migrate(cr, version):
    """Draft preinvoices must not reserve inventory before confirmation."""
    cr.execute(
        """
        UPDATE account_move
           SET ddsn_reservation_expires_at = NULL
         WHERE ddsn_is_preinvoice = TRUE
           AND COALESCE(ddsn_preinvoice_state, 'draft') = 'draft'
        """
    )

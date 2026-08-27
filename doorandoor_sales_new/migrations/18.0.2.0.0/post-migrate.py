def migrate(cr, version):
    """Classify existing linked draft customer documents as preinvoices."""
    cr.execute(
        """
        UPDATE account_move
           SET ddsn_is_preinvoice = TRUE,
               ddsn_preinvoice_state = COALESCE(ddsn_preinvoice_state, 'draft')
         WHERE move_type = 'out_invoice'
           AND state = 'draft'
           AND sale_order_id IS NOT NULL
           AND ddsn_source_preinvoice_id IS NULL
           AND COALESCE(ddsn_is_preinvoice, FALSE) = FALSE
        """
    )

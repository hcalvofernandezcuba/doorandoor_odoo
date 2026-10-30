# -*- coding: utf-8 -*-
"""
DoorAndDoor - Botón de Entrega desde Ventas
Modelo: sale.order
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # -------------------------------------------------------------------------
    # CAMPOS
    # -------------------------------------------------------------------------

    delivery_count = fields.Integer(
        string='Cantidad de Entregas',
        compute='_compute_delivery_count',
        store=False,
        help='Número de pickings de entrega relacionados a esta venta'
    )

    delivery_ids = fields.One2many(
        'stock.picking',
        'sale_id',
        string='Entregas Relacionadas',
        help='Pickings de entrega vinculados a este pedido de venta'
    )

    dddb_delivery_enabled = fields.Boolean(
        string='Delivery Enabled',
        compute='_compute_dddb_delivery_controls',
        help='Indica si la entrega puede gestionarse segun el pago total de la factura vinculada.'
    )

    dddb_delivery_block_reason = fields.Char(
        string='Delivery Block Reason',
        compute='_compute_dddb_delivery_controls',
    )

    # -------------------------------------------------------------------------
    # MÉTODOS COMPUTE
    # -------------------------------------------------------------------------

    @api.depends('delivery_ids')
    def _compute_delivery_count(self):
        """Calcula la cantidad de entregas relacionadas a la venta."""
        for order in self:
            order.delivery_count = len(order.delivery_ids)

    @api.depends(
        'state',
        'invoice_ids.state',
        'invoice_ids.payment_state',
        'invoice_ids.amount_total',
        'invoice_ids.amount_residual',
    )
    def _compute_dddb_delivery_controls(self):
        for order in self:
            enabled, reason = order._dddb_get_delivery_authorization()
            order.dddb_delivery_enabled = enabled
            order.dddb_delivery_block_reason = reason

    def _dddb_get_delivery_invoices(self):
        self.ensure_one()
        invoices = self.invoice_ids
        AccountMove = self.env['account.move']
        if 'sale_order_id' in AccountMove._fields:
            invoices |= AccountMove.search([
                ('sale_order_id', '=', self.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '!=', 'cancel'),
            ])
        if 'ddsn_invoice_move_id' in self._fields:
            invoices |= self.ddsn_invoice_move_id
        return invoices.filtered(
            lambda invoice: invoice.move_type == 'out_invoice'
            and invoice.state != 'cancel'
            and not getattr(invoice, 'ddsn_is_preinvoice', False)
        )

    def _dddb_get_delivery_authorization(self):
        self.ensure_one()
        if self.state not in ('sale', 'done'):
            return False, _('La cotizacion debe estar confirmada antes de gestionar una entrega.')

        invoices = self._dddb_get_delivery_invoices()
        if not invoices:
            return False, _(
                'No existe una factura fiscal vinculada. Las cotizaciones y prefacturas no autorizan entregas.'
            )
        if any(invoice.state != 'posted' for invoice in invoices):
            return False, _('Todas las facturas vinculadas deben estar publicadas antes de entregar.')
        if not all(self._dddb_is_invoice_fully_paid(invoice) for invoice in invoices):
            return False, _(
                'La entrega permanece bloqueada hasta que todas las facturas vinculadas esten totalmente pagadas.'
            )
        return True, False

    def _dddb_assert_delivery_allowed(self):
        for order in self:
            enabled, reason = order._dddb_get_delivery_authorization()
            if not enabled:
                raise UserError(reason)
        return True

    def _dddb_is_invoice_fully_paid(self, invoice):
        self.ensure_one()
        currency = invoice.currency_id
        total_amount = abs(invoice.amount_total)
        residual_amount = abs(invoice.amount_residual)
        if hasattr(invoice, '_ddsn_is_fully_paid'):
            return bool(total_amount and not currency.is_zero(total_amount) and invoice._ddsn_is_fully_paid())
        return bool(
            total_amount
            and not currency.is_zero(total_amount)
            and currency.is_zero(residual_amount)
            and invoice.payment_state == 'paid'
        )

    # -------------------------------------------------------------------------
    # MÉTODOS DE ACCIÓN
    # -------------------------------------------------------------------------

    def action_open_delivery(self):
        """
        Acción principal del botón "Entregar".

        Flujo:
        1. Valida que la venta esté confirmada
        2. Busca pickings de tipo 'outgoing' en estado 'draft' vinculados a esta venta
        3. Si existe en borrador: abre ese picking en formulario
        4. Si no existe en borrador pero hay validado: abre el validado (decisión B)
        5. Si no existe ninguno: crea uno nuevo

        Returns:
            dict: Action window para abrir el picking (form o tree)
        """
        self.ensure_one()

        if not self.env.context.get("dddb_delivery_from_authorized_invoice"):
            raise UserError(_(
                "Las entregas no se gestionan desde Presupuestos, Órdenes de Venta "
                "ni prefacturas. Utilice la factura autorizada y las operaciones de Inventario."
            ))

        # Validar estado de la venta
        if self.state != 'sale':
            raise UserError(_(
                'Solo se pueden gestionar entregas de pedidos de venta confirmados. '
                'El estado actual es: %s'
            ) % self.state)

        self._dddb_assert_delivery_allowed()

        # Buscar pickings relacionados
        Picking = self.env['stock.picking']

        # Primero buscar en borrador (prioridad máxima)
        draft_pickings = Picking.search([
            ('sale_id', '=', self.id),
            ('picking_type_id.code', '=', 'outgoing'),
            ('state', '=', 'draft'),
        ], order='create_date desc')

        if draft_pickings:
            # Abrir el picking en borrador más reciente
            return self._action_open_picking_form(draft_pickings[0])

        # Si no hay en borrador, buscar cualquier picking relacionado (validados)
        all_pickings = Picking.search([
            ('sale_id', '=', self.id),
            ('picking_type_id.code', '=', 'outgoing'),
        ], order='create_date desc')

        if all_pickings:
            # Decisión B: Abrir el picking validado (o el más reciente)
            return self._action_open_picking_form(all_pickings[0])

        # No existe picking: crear uno nuevo
        new_picking = self._create_delivery_picking()
        return self._action_open_picking_form(new_picking)

    def _create_delivery_picking(self):
        """
        Crea un nuevo picking de entrega para esta venta.

        Determina:
        - Almacén según warehouse_id de la venta o compañía
        - Tipo de operación: 'outgoing' del almacén
        - Ubicaciones origen/destino con fallback robusto
        - Líneas de movimiento desde las líneas de venta (solo productos stockeables)

        Returns:
            stock.picking: El picking recién creado
        """
        self.ensure_one()
        self._dddb_assert_delivery_allowed()

        # Determinar almacén: primero warehouse_id de la venta, luego compañía
        warehouse = self.warehouse_id
        if not warehouse:
            warehouse = self.env.user.company_id.warehouse_id

        if not warehouse:
            raise UserError(_(
                'No se encontró un almacén configurado para la compañía %s. '
                'Por favor configure un almacén en Ajustes > Usuarios y Compañías > Compañías.'
            ) % self.company_id.name)

        # Verificar que el almacén pertenezca a la compañía de la venta
        if warehouse.company_id != self.company_id:
            # Buscar almacén de la compañía de la venta
            warehouse = self.env['stock.warehouse'].search([
                ('company_id', '=', self.company_id.id),
            ], limit=1)
            if not warehouse:
                raise UserError(_(
                    'No se encontró un almacén para la compañía %s.'
                ) % self.company_id.name)

        picking_type = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', warehouse.id),
            ('code', '=', 'outgoing'),
        ], limit=1)

        if not picking_type:
            raise UserError(_(
                'No se encontró un tipo de operación "Entregas" para el almacén %s.'
            ) % warehouse.name)

        # Determinar ubicaciones con fallback robusto
        location_src = picking_type.default_location_src_id or warehouse.lot_stock_id
        location_dest = picking_type.default_location_dest_id or self.partner_id.property_stock_customer

        # Fallback final para ubicación destino
        if not location_dest:
            # Buscar ubicación de cliente genérica
            location_dest = self.env.ref('stock.stock_location_customers', raise_if_not_found=False)
            if not location_dest:
                raise UserError(_(
                    'No se encontró una ubicación de destino para el cliente. '
                    'Por favor configure la ubicación de stock del cliente %s.'
                ) % self.partner_id.name)

        # Preparar valores del picking
        picking_vals = {
            'partner_id': self.partner_shipping_id.id or self.partner_id.id,
            'picking_type_id': picking_type.id,
            'location_id': location_src.id,
            'location_dest_id': location_dest.id,
            'origin': self.name,
            'sale_id': self.id,
            'company_id': self.company_id.id,
            'scheduled_date': fields.Datetime.now(),
            'move_type': self.picking_policy or 'direct',
        }

        # Crear el picking
        picking = self.env['stock.picking'].create(picking_vals)

        # Crear las líneas de movimiento desde las líneas de venta
        self._create_stock_moves_from_sale_lines(picking)

        # Registrar en el chatter de la venta
        self.message_post(
            body=_('Se creó la entrega <a href="#" data-oe-model="stock.picking" data-oe-id="%s">%s</a> desde el botón de entregas.') % (picking.id, picking.name)
        )

        return picking

    def _create_stock_moves_from_sale_lines(self, picking):
        """
        Crea los stock.move desde las líneas de venta para un picking dado.

        Solo incluye productos de tipo 'product' (stockeable) o 'consu' (consumible).
        Los productos de tipo 'service' se ignoran.

        La cantidad a entregar se calcula como: cantidad pedida - cantidad entregada
        en pickings validados. Los pickings en borrador no afectan este cálculo
        para permitir correcciones.

        Args:
            picking (stock.picking): El picking donde agregar los movimientos
        """
        self.ensure_one()

        move_vals_list = []

        for line in self.order_line:
            # Solo productos stockeables y consumibles
            if line.product_id.type not in ['product', 'consu']:
                continue

            # Calcular cantidad pendiente de entregar
            # qty_delivered ya considera pickings validados en Odoo estándar
            qty_to_deliver = line.product_uom_qty - line.qty_delivered
            if qty_to_deliver <= 0:
                continue

            move_vals = {
                'picking_id': picking.id,
                'product_id': line.product_id.id,
                'product_uom_qty': qty_to_deliver,
                'product_uom': line.product_uom.id,
                'name': line.name or line.product_id.name,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'sale_line_id': line.id,
                'origin': self.name,
                'company_id': self.company_id.id,
                'state': 'draft',
            }
            move_vals_list.append(move_vals)

        if move_vals_list:
            self.env['stock.move'].create(move_vals_list)
            picking.message_post(
                body=_('Se agregaron %s líneas de movimiento desde el pedido de venta %s.') % (len(move_vals_list), self.name)
            )
        else:
            # Si no hay productos stockeables, mostrar advertencia pero no bloquear
            picking.message_post(
                body=_(
                    '⚠️ Este pedido no contiene productos stockeables pendientes de entregar. '
                    'El picking fue creado sin líneas de movimiento.'
                )
            )

    def _action_open_picking_form(self, picking):
        """
        Retorna la acción para abrir un picking en formulario.

        Args:
            picking (stock.picking): El picking a abrir

        Returns:
            dict: Action window
        """
        return {
            'type': 'ir.actions.act_window',
            'name': _('Entrega: %s') % picking.name,
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'view_mode': 'form',
            'view_id': self.env.ref('stock.view_picking_form').id,
            'target': 'current',
            'context': {
                'default_picking_type_id': picking.picking_type_id.id,
                'from_sale_order': True,
                'sale_order_id': self.id,
            },
        }

    def action_view_delivery(self):
        """
        Acción para el stat button (botón inteligente).
        Abre la lista de entregas relacionadas o el formulario si hay una sola.

        Returns:
            dict: Action window (tree o form)
        """
        self.ensure_one()
        raise UserError(_(
            "Las entregas no se consultan desde Presupuestos, Órdenes de Venta "
            "ni prefacturas. Consulte la factura autorizada o Inventario."
        ))

        if self.delivery_count == 0:
            # No hay entregas: crear una nueva
            return self.action_open_delivery()

        if self.delivery_count == 1:
            # Una sola entrega: abrir formulario
            return self._action_open_picking_form(self.delivery_ids[0])

        # Múltiples entregas: abrir vista lista
        return {
            'type': 'ir.actions.act_window',
            'name': _('Entregas de %s') % self.name,
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('sale_id', '=', self.id)],
            'context': {
                'default_sale_id': self.id,
                'search_default_outgoing': 1,
                'from_sale_order': True,
                'sale_order_id': self.id,
            },
        }

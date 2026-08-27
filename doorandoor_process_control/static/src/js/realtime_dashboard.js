odoo.define('doorandoor_process_control.RealtimeDashboard', function (require) {
    "use strict";
    
    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var KanbanRenderer = require('web.KanbanRenderer');
    var session = require('web.session');
    var core = require('web.core');
    var _t = core._t;
    
    /**
     * Renderer personalizado para el dashboard con actualización en tiempo real
     */
    var RealtimeDashboardRenderer = KanbanRenderer.extend({
        events: _.extend({}, KanbanRenderer.prototype.events, {
            'click .o_ddpc_open_picking': '_onOpenPicking',
            'click .o_ddpc_validate_receipt': '_onValidateReceipt',
        }),
        
        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            this.bus = session.bus;
            this._updateTimer = null;
            this.autoRefresh = true;
            this.refreshInterval = 30000; // 30 segundos
        },
        
        start: function () {
            var self = this;
            this._super.apply(this, arguments);
            
            // Suscribirse al canal de actualizaciones
            this.bus.on('doorandoor.picking.update', this, this._onPickingUpdate);
            this.bus.add_channel('doorandoor.picking.update');
            
            // Iniciar actualización automática
            if (this.autoRefresh) {
                this._startAutoRefresh();
            }
            
            // Mostrar indicador de conexión
            this._showConnectionStatus();
        },
        
        destroy: function () {
            this._stopAutoRefresh();
            if (this.bus) {
                this.bus.remove_channel('doorandoor.picking.update');
                this.bus.off('doorandoor.picking.update', this, this._onPickingUpdate);
            }
            this._super.apply(this, arguments);
        },
        
        _startAutoRefresh: function () {
            var self = this;
            this._updateTimer = setInterval(function () {
                self._reloadDashboard();
            }, this.refreshInterval);
        },
        
        _stopAutoRefresh: function () {
            if (this._updateTimer) {
                clearInterval(this._updateTimer);
                this._updateTimer = null;
            }
        },
        
        _reloadDashboard: function () {
            var self = this;
            this.trigger_up('reload', {
                keepChanges: true,
                onSuccess: function () {
                    self._showRefreshIndicator();
                }
            });
        },
        
        _onPickingUpdate: function (message) {
            var self = this;
            
            // Solo actualizar si el picking está en el dashboard actual
            var pickingId = message.picking_id;
            var card = this.$('.o_kanban_record[data-id="' + pickingId + '"]');
            
            if (card.length) {
                // Actualizar tarjeta específica
                this._updateCard(card, message);
                this._showNotification(message);
            } else {
                // Si no está visible, recargar el dashboard
                this._reloadDashboard();
            }
        },
        
        _updateCard: function ($card, message) {
            // Actualizar estado en tiempo real
            var $status = $card.find('.o_ddpc_realtime_status');
            if ($status.length) {
                var statusText = message.ddpc_realtime_status || message.state || _t('Desconocido');
                $status.text(statusText);
                
                // Actualizar clases según estado
                $status.removeClass('text-warning text-success text-info text-danger');
                if (message.state === 'done') {
                    $status.addClass('text-success');
                } else if (message.ddpc_transfer_stage === 'dispatch') {
                    $status.addClass('text-warning');
                } else {
                    $status.addClass('text-info');
                }
            }
            
            // Actualizar timestamp
            var $timestamp = $card.find('.o_ddpc_last_update');
            if ($timestamp.length && message.timestamp) {
                var date = new Date(message.timestamp);
                $timestamp.text(date.toLocaleTimeString());
            }
            
            // Actualizar badge de etapa
            var $stageBadge = $card.find('.o_ddpc_stage_badge');
            if ($stageBadge.length && message.ddpc_transfer_stage) {
                $stageBadge.text(message.ddpc_transfer_stage === 'dispatch' ? _t('Despacho') : _t('Recepción'));
                $stageBadge.removeClass('badge-warning badge-info badge-success');
                if (message.ddpc_transfer_stage === 'dispatch') {
                    $stageBadge.addClass('badge-warning');
                } else {
                    $stageBadge.addClass('badge-info');
                }
            }
            
            // Añadir animación de actualización
            $card.addClass('o_ddpc_updating');
            setTimeout(function () {
                $card.removeClass('o_ddpc_updating');
            }, 1000);
        },
        
        _showNotification: function (message) {
            var notificationOptions = {
                type: 'info',
                title: _t('Actualización de Traslado'),
                message: '',
                sticky: false,
            };
            
            if (message.event === 'transfer_dispatched') {
                notificationOptions.message = _t('Traslado %s despachado hacia %s').format(
                    message.picking_name,
                    message.dest_warehouse
                );
                notificationOptions.type = 'warning';
            } else if (message.event === 'transfer_received') {
                notificationOptions.message = _t('Recepción de %s validada').format(
                    message.picking_name
                );
                notificationOptions.type = 'success';
            } else {
                notificationOptions.message = _t('Actualización: %s').format(message.event || _t('Estado cambiado'));
            }
            
            this.do_notify(notificationOptions.title, notificationOptions.message);
        },
        
        _showConnectionStatus: function () {
            var $status = this.$('.o_ddpc_connection_status');
            if ($status.length) {
                $status.addClass('show');
            }
        },
        
        _showRefreshIndicator: function () {
            var self = this;
            var $indicator = $('<div class="o_ddpc_refresh_indicator">');
            $indicator.text(_t('Actualizado'));
            this.$el.append($indicator);
            
            setTimeout(function () {
                $indicator.fadeOut(function () {
                    $indicator.remove();
                });
            }, 2000);
        },
        
        _onOpenPicking: function (e) {
            e.preventDefault();
            e.stopPropagation();
            
            var $card = $(e.currentTarget).closest('.o_kanban_record');
            var recordId = $card.data('id');
            
            this.trigger_up('open_record', {
                id: recordId,
                mode: 'edit',
            });
        },
        
        _onValidateReceipt: function (e) {
            e.preventDefault();
            e.stopPropagation();
            
            var self = this;
            var $card = $(e.currentTarget).closest('.o_kanban_record');
            var recordId = $card.data('id');
            
            // Confirmar acción
            if (confirm(_t('¿Validar la recepción de este traslado?'))) {
                this._rpc({
                    model: 'stock.picking',
                    method: 'button_validate',
                    args: [[recordId]],
                }).then(function () {
                    self._reloadDashboard();
                    self.do_notify(_t('Éxito'), _t('Recepción validada correctamente'));
                }).fail(function () {
                    self.do_notify(_t('Error'), _t('No se pudo validar la recepción'), true);
                });
            }
        },
    });
    
    /**
     * Vista personalizada para el dashboard
     */
    var RealtimeDashboardView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Renderer: RealtimeDashboardRenderer,
        }),
    });
    
    // Registrar la vista
    core.view_registry.add('doorandoor_process_control.RealtimeDashboard', RealtimeDashboardView);
    
    return RealtimeDashboardView;
});
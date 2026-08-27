odoo.define('doorandoor_process_control.RealtimePickingWidget', function (require) {
    "use strict";
    
    var Widget = require('web.Widget');
    var session = require('web.session');
    var core = require('web.core');
    var _t = core._t;
    
    /**
     * Widget para actualización en tiempo real de pickings de traslados.
     * Escucha notificaciones del bus.bus y actualiza la interfaz automáticamente.
     */
    var RealtimePickingWidget = Widget.extend({
        template: 'doorandoor_process_control.RealtimePickingTemplate',
        
        events: {
            'click .o_ddpc_refresh_manual': '_onManualRefresh',
        },
        
        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.picking_id = options.picking_id || false;
            this.autoRefresh = options.autoRefresh !== false; // Por defecto true
            this.refreshInterval = options.refreshInterval || 30000; // 30 segundos por defecto
            this.bus = session.bus;
            this._pollingTimer = null;
        },
        
        start: function () {
            var self = this;
            this._super.apply(this, arguments);
            
            if (this.picking_id) {
                // Suscribirse al canal de actualizaciones de pickings
                this.bus.on('doorandoor.picking.update', this, this._onPickingUpdate);
                this.bus.add_channel('doorandoor.picking.update');
                
                // Iniciar polling como fallback
                if (this.autoRefresh) {
                    this._startPolling();
                }
                
                // Actualización inicial
                this._updateDisplay();
            }
            
            return this._super();
        },
        
        destroy: function () {
            this._stopPolling();
            if (this.bus) {
                this.bus.remove_channel('doorandoor.picking.update');
                this.bus.off('doorandoor.picking.update', this, this._onPickingUpdate);
            }
            this._super.apply(this, arguments);
        },
        
        _startPolling: function () {
            var self = this;
            this._pollingTimer = setInterval(function () {
                self._doPoll();
            }, this.refreshInterval);
        },
        
        _stopPolling: function () {
            if (this._pollingTimer) {
                clearInterval(this._pollingTimer);
                this._pollingTimer = null;
            }
        },
        
        _doPoll: function () {
            var self = this;
            if (!this.picking_id) return;
            
            this._rpc({
                model: 'stock.picking',
                method: 'read',
                args: [[this.picking_id], ['ddpc_realtime_status', 'ddpc_last_activity_timestamp', 'state', 'ddpc_transfer_stage']],
            }).then(function (result) {
                if (result && result.length > 0) {
                    var picking = result[0];
                    self._updateDisplay({
                        ddpc_realtime_status: picking.ddpc_realtime_status,
                        ddpc_last_activity_timestamp: picking.ddpc_last_activity_timestamp,
                        state: picking.state,
                        ddpc_transfer_stage: picking.ddpc_transfer_stage,
                    });
                }
            });
        },
        
        _onPickingUpdate: function (message) {
            // Procesar mensaje del bus si corresponde a este picking
            if (this.picking_id && message.picking_id === this.picking_id) {
                this._updateDisplay(message);
                this._showNotification(message);
            }
        },
        
        _onManualRefresh: function (e) {
            e.preventDefault();
            this._doPoll();
        },
        
        _updateDisplay: function (data) {
            if (!data) return;
            
            // Actualizar estado en tiempo real
            var $status = this.$('.o_ddpc_realtime_status');
            if ($status.length) {
                var statusText = data.ddpc_realtime_status || data.state || _t('Desconocido');
                $status.text(statusText);
                
                // Actualizar clases según estado
                $status.removeClass('text-warning text-success text-info text-danger');
                if (data.ddpc_transfer_stage === 'dispatch') {
                    $status.addClass('text-warning');
                } else if (data.ddpc_transfer_stage === 'receipt' && data.state === 'done') {
                    $status.addClass('text-success');
                } else if (data.ddpc_transfer_stage === 'receipt') {
                    $status.addClass('text-info');
                }
            }
            
            // Actualizar timestamp
            var $timestamp = this.$('.o_ddpc_last_update');
            if ($timestamp.length) {
                var timestamp = data.ddpc_last_activity_timestamp || data.timestamp;
                if (timestamp) {
                    var date = new Date(timestamp);
                    $timestamp.text(date.toLocaleTimeString());
                }
            }
            
            // Actualizar badge de etapa
            var $stageBadge = this.$('.o_ddpc_stage_badge');
            if ($stageBadge.length && data.ddpc_transfer_stage) {
                $stageBadge.text(data.ddpc_transfer_stage === 'dispatch' ? _t('Despacho') : _t('Recepción'));
                $stageBadge.removeClass('badge-warning badge-info badge-success');
                if (data.ddpc_transfer_stage === 'dispatch') {
                    $stageBadge.addClass('badge-warning');
                } else {
                    $stageBadge.addClass('badge-info');
                }
            }
        },
        
        _showNotification: function (message) {
            var self = this;
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
                notificationOptions.message = _t('Recepción de %s validada por %s').format(
                    message.picking_name,
                    message.validated_by
                );
                notificationOptions.type = 'success';
            } else {
                notificationOptions.message = _t('Actualización: %s').format(message.event || _t('Estado cambiado'));
            }
            
            // Usar el sistema de notificaciones de Odoo
            this.do_notify(notificationOptions.title, notificationOptions.message);
        },
    });
    
    return RealtimePickingWidget;
});
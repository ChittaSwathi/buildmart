odoo.define('buildmart.grid_view', function (require) {
"use strict";

/**
 * This widget render a Pie Chart. It is used in the dashboard view.
 */

var core = require('web.core');
var Domain = require('web.Domain');
var viewRegistry = require('web.view_registry');
var Widget = require('web.Widget');
var widgetRegistry = require('web.widget_registry');
const { loadLegacyViews } = require("@web/legacy/legacy_views");

var qweb = core.qweb;

var GridView = Widget.extend({
    className: 'o_list_view',
    xmlDependencies: ['/buildmart/static/src/legacy/xml/grid.xml'],

    /**
     * @override
     * @param {Widget} parent
     * @param {Object} record
     * @param {Object} node node from arch
     */
    init: function (parent, record, node) {
        this._super.apply(this, arguments);

        var modifiers = node.attrs.modifiers;
        var domain = record.domain;
        var arch = qweb.render('buildmart.Grid', {});

        this.subViewParams = {
            modelName: record.model,
            withButtons: false,
            withControlPanel: false,
            withSearchPanel: false,
            isEmbedded: true,
            useSampleModel: record.isSample,
            mode: 'list',
            limit:80,
        };
        this.subViewParams.searchQuery = {
            context: {},
            domain: domain,
            groupBy: [],
            timeRanges: record.timeRanges || {},
            
        };

        this.viewInfo = {
            arch: arch,
            fields: record.fields,
            viewFields: record.fieldsInfo.dashboard,
        };
    },
    /**
     * Instantiates the pie chart view and starts the graph controller.
     *
     * @override
     */
    willStart: async function () {
        var self = this;
        const _super = this._super.bind(this, ...arguments);
        await loadLegacyViews({ rpc: this._rpc.bind(this) });
        var def1 = _super();
        var SubView = viewRegistry.get('list');
        var subView = new SubView(this.viewInfo, this.subViewParams);
        var def2 = subView.getController(this).then(function (controller) {
            self.controller = controller;
            return self.controller.appendTo(document.createDocumentFragment());
        });
        return Promise.all([def1,def2]);
    },
    /**
     * @override
     */
    start: function () {
        this.$el.append(this.controller.$el);
        if(this.$el){
        	if(this.$el.find('table')){
		        this.$el.find('table').attr("style", "table-layout: fixed");
		        console.log(this.$el.find('table').find('thead'));
		        var string = ['','Order', 'Invoice','Bill No.','Transport Name','Quantity','UoM','Amount','Status']
		        this.$el.find('table').find('thead').find('th').each(function (index ) {
				     if(index > 0){
				     	$(this).text(string[index]);
				     }
				});
			}
		}
        return this._super.apply(this, arguments);
    },
    /**
     * Call `on_attach_callback` for each subview
     *
     * @override
     */
    
});

widgetRegistry.add('grid_view', GridView);

return GridView;

});

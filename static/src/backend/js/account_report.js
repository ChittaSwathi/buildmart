
odoo.define('buildmart.account_report', function (require) {
"use strict";

var core = require('web.core');
var AbstractReport = require('account_reports.account_report');
var AbstractAction = require('web.AbstractAction');
var QWeb = core.qweb;
var _t = core._t;



var accountReportsWidget = AbstractReport.include({

	 events: _.extend({}, AbstractReport.prototype.events, {
           'click #display_sitename': '_onClickSiteName',
        }),
        
    _onClickSiteName: function (ev) {
    	var self = this;
    	var chk_value = $('#display_sitename').is(':checked');
        if ($('#display_sitename').is(':checked'))
			{
				this.report_options.sitename = true;
			}else{
			   this.report_options.sitename = false;
			}
        return self.reload().then(function () {
                 if (chk_value)
					{
						$('#display_sitename').prop('checked', true);
						$(".sitename").show();
					}else{
						$('#display_sitename').prop('checked', false);
					  $(".sitename").hide();
					}
             });
    },
	
});


});

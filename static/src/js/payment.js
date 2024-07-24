odoo.define('buildmart.payment', require => {
    'use strict';

    const checkoutForm = require('payment.checkout_form');

    const websiteSalePaymentMixin = {

        /**
         * @override
         */
        init: function () {
            this._onClickTCCheckbox = _.debounce(this._onClickTCCheckbox, 100, true);
            this._super(...arguments);
        },

        /**
         * @override
         */
        start: function () {
            this.$checkbox = this.$('#checkbox_tc');
            this.$submitButton = this.$('button[name="o_payment_submit_button"]');
            this._adaptConfirmButton();
            return this._super(...arguments);
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Update the data on the submit button with the status of the Terms and Conditions input.
         *
         * @private
         * @return {undefined}
         */
        _adaptConfirmButton: function () {
            if (this.$checkbox.length > 0) {
                const disabledReasons = this.$submitButton.data('disabled_reasons') || {};
                disabledReasons.tc = !this.$checkbox.prop('checked');
                this.$submitButton.data('disabled_reasons', disabledReasons);
            }
        },

    };

    checkoutForm.include(Object.assign({}, websiteSalePaymentMixin, {
        

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * Verify that the Terms and Condition checkbox is checked.
         *
         * @override method from payment.payment_form_mixin
         * @private
         * @return {boolean} Whether the submit button can be enabled
         */
        _isButtonReady: function () {
			debugger;
			const $checkedRadios = this.$('input[name="o_payment_radio"]:checked');
            if ($checkedRadios.length === 1) {
                const checkedRadio = $checkedRadios[0];
                const flow = this._getPaymentFlowFromRadio(checkedRadio);
                return flow !== 'token' || this.txContext.allowTokenSelection;
            } else {
                return false;
            }
           
        },
		
        
    }));

    
});

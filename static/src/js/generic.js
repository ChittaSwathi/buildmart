odoo.define('buildmart.bs_generic', function(require) {
    "use strict";

    require('web.dom_ready');
    var ajax = require('web.ajax');
    var rpc = require("web.rpc");
    var MobileRegex = /^\d*[0-9-+](|.\d*[0-9-+]|,\d*[0-9-+])?$/;
    var AllCharsRegex = /^[ A-Za-z]+$/;
    var GSTRegex = /^([0][1-9]|[1-2][0-9]|[3][0-7])([a-zA-Z]{5}[0-9]{4}[a-zA-Z]{1}[1-9a-zA-Z]{1}[zZ]{1}[0-9a-zA-Z]{1})+$/;
    var core = require('web.core');
    var Dialog = require('web.Dialog');
    var publicWidget = require('web.public.widget');
    var QWeb = core.qweb;
    var _t = core._t;
    var Widget = require('web.Widget');
    const wUtils = require('website.utils');

    // state date end date validations
    $(function(){
        var dtToday = new Date();
        var month = dtToday.getMonth() + 1;
        var day = dtToday.getDate();
        var year = dtToday.getFullYear();
        if(month < 10) month = '0' + month.toString();
        if(day < 10) day = '0' + day.toString();
        var minDate= year + '-' + month + '-' + day;
        $('#requested_del_date').attr('min', minDate);
        $('#order_st_date').attr('max', minDate);
        $('#odr_end_date').attr('max', minDate);
    });

    var start = document.getElementById('order_st_date');
    var end = document.getElementById('odr_end_date');
    function showEnd() {
      if (end.value){
        start.max = end.value;
      }
    }
    function showStart(){
        if (start.value){
            end.min = start.value;
        }
        if(end.value){
            var dateOne = new Date(start.value);
            var dateTwo = new Date(end.value);
            if (dateOne <= dateTwo) {
            }else {
                end.value = '';
            }
        }
    }
    if(end != null){
        end.addEventListener('change', showEnd, false);
    }
    if(start != null){
        start.addEventListener('change', showStart, false);
    }
    // start date end date validations

    // /my/home & Internal Pages JS starts
    $(".bs-account .nav-tabs li a").click(function (){
        $(".nav-tabs li").removeClass("active");
        $(this).parent().addClass("active");
    });
    $('.bs-account .collapse').on('shown.bs.collapse', function () {
        $(this).parent().addClass('active');
    });
    $('.bs-account .collapse').on('hidden.bs.collapse', function () {
        $(this).parent().removeClass('active');
    });


    // show more hide and show in profile pages
    $(function() {
        $('.line-text-clamp').each(function(i) {
            var element = $(this).clone().css({display: 'inline', width: 'auto', visibility: 'hidden'}).appendTo('body');
            if( element.width() > $(this).width() ) {
                $(this).next().css({"display": "show"});
            }else{
                $(this).next().css({"display": "none"});
            }
            element.remove();
        });
    });
    // show more hide and show in profile pages

    // click & upload --- starts
    function encodeImageFileAsURL(cb) {
        return function(){
            var file = this.files[0];
            var reader  = new FileReader();
            reader.onloadend = function () { cb(reader.result); }
            reader.readAsDataURL(file);
        }
    }
    /* Generic function that returns base64 string */

    publicWidget.registry.clickUpload = publicWidget.Widget.extend({
        selector: '.click-upload',
        events: {
            // 'change #enquiry_attachment':  '_onChangeEnqAttach',
            // 'change #delivery_attachment':  '_onChangeDelAttach',
            'change #contact_person': '_onchangeContPersn',
            'change #phone': '_onchangePhn',
            'change #gstin': '_onchangeGSTIN',
            'change #trade_name': '_onchangeTradeName',
            'change #address': '_onchangeAddress',
            'click #submit_click_upload': '_onSubmitForm',
        },
        init: function() {
            this._super.apply(this, arguments);
        },
        readURL: function(input, EleID, Eleb64) {
            if (input.files && input.files[0]) {
                var reader = new FileReader();
                reader.onload = function(e) {
                    $('#'+EleID).css('background-image', 'url('+e.target.result +')');
                    $('#'+EleID).hide();
                    $('#'+EleID).fadeIn(650);
                    $(Eleb64+'_base64').val(e.target.result.replace(/^data:.+;base64,/, '')).attr('src',e.target.result);
                    $(Eleb64+'_label').html(input.files[0]['name']);
                }
                reader.readAsDataURL(input.files[0]);
            }
        },
        _onChangeEnqAttach: function(base64Img){
            this.readURL(base64Img.target, 'enq-attach-preview','#enquiry_attachment');
        },
        _onChangeDelAttach: function(base64Img){
            this.readURL(base64Img.target, 'del-attach-preview', '#delivery_attachment');
        },
        _onchangeContPersn: function(e){
            var Name = e.target.value
            if ((Name.length == 0) || (!AllCharsRegex.test(Name))) {
                $("#"+ e.target.id +"_error").html("Please enter a valid name.").show();
            } else {
                $("#"+ e.target.id +"_error").html("").hide();
            }
        },
        _onchangePhn: function(e){
            var Phone = e.target.value
            if ((Phone.length < 10) || (!MobileRegex.test(Phone))) {
                $("#"+ e.target.id +"_error").html("Please enter a valid phone number.").show();
            } else {
                $("#"+ e.target.id +"_error").html("").hide();
            }
        },
        _onchangeGSTIN: function(e){
            var GST = e.target.value
            if ((GST.length != 15) || (!GSTRegex.test(GST))) {
                if (($('#customer-type').val() == 'b2c' && GST.length == 0)){
                    $("#"+ e.target.id +"_error").html("").hide();
                }
                else{
                    $("#"+ e.target.id +"_error").html("Please enter a valid GSTIN.").show();
                }
            } else {
                $("#"+ e.target.id +"_error").html("").hide();
            }
        },
        _onchangeTradeName: function(e){
            var TName = e.target.value
            if (TName.length == 0) {
                if (($('#customer-type').val() == 'b2c' && TName.length == 0)){
                    $("#"+ e.target.id +"_error").html("").hide();
                }
                else{
                    $("#"+ e.target.id +"_error").html("Please enter a valid trade name.").show();
                }
            } else {
                $("#"+ e.target.id +"_error").html("").hide();
            }
        },
        _onchangeAddress:function(e){
            var AName = e.target.value
            if (AName.length == 0) {
                $("#"+ e.target.id +"_error").html("Please enter your registered address.").show();
            } else {
                $("#"+ e.target.id +"_error").html("").hide();
            }
        },
        _onSubmitForm: function(e){
            var valid = true;
            var FinalVals = {}
            //FinalVals['documents'] = uploadFileAttachmentObj;
            //var Name = $('#full_name').val();
            //FinalVals['name'] = Name;
            //var Phone = $('#phone').val();
            //FinalVals['phone'] = Phone;
            $('#click-upload-form input:visible').each(function(){

                var inputName = $(this).attr("name");
                console.log(inputName);
                if(inputName == 'enq_attachment'){
                    var isEmptyenqObj = jQuery.isEmptyObject(uploadEnquiryObj);
                    if(isEmptyenqObj === true){
                        valid = false;
                        $("#"+ $(this).attr("id") +"_error").html("Please upload enquiry attachment file or image.").show();
                    }else{
                        $("#"+ $(this).attr("id") +"_error").html("").hide();
                        FinalVals['documents'] = uploadEnquiryObj
                    }
                }
                /*if(inputName == 'delivery_attachment'){
                    var isEmptyenqDelObj = jQuery.isEmptyObject(uploadDeliveryObj);
                    if(isEmptyenqDelObj === true){
                        valid = false;
                        $("#"+ $(this).attr("id") +"_error").html("Please upload delivery attachment file or image.").show();
                    }else{
                        $("#"+ $(this).attr("id") +"_error").html("").hide();
                        FinalVals['delivery'] = uploadDeliveryObj
                    }
                }*/
               if(inputName == 'full_name'){
                    var Name = $(this).val();
                    if ((Name.length == 0) || (!AllCharsRegex.test(Name))) {
                        valid = false;
                        $("#"+ $(this).attr("id") +"_error").html("Please enter a valid name.").show();
                    } else {
                        $("#"+ $(this).attr("id") +"_error").html("").hide();
                        FinalVals['name'] = Name
                    }
                }
                if(inputName == 'phone'){
                    var Phone = $(this).val();
                    if ((Phone.length < 10) || (!MobileRegex.test(Phone))) {
                        valid = false;
                        $("#"+ $(this).attr("id") +"_error").html("Please enter a valid phone number.").show();
                    } else {
                        $("#"+ $(this).attr("id") +"_error").html("").hide();
                        FinalVals['phone'] = Phone
                    }
                }
                if(inputName == 'alter_phone'){
                    var alter_phone = $(this).val();
                    if ((alter_phone.length < 10) || (!MobileRegex.test(alter_phone))) {
                        valid = false;
                        $("#"+ $(this).attr("id") +"_error").html("Please enter a valid phone number.").show();
                    } else {
                        $("#"+ $(this).attr("id") +"_error").html("").hide();
                        FinalVals['alt_phone_no'] = alter_phone
                    }
                }
                if(inputName == 'location'){
                    var location = $(this).val();
                    FinalVals['address'] = location;
                }
                if(inputName == 'material'){
                    var material = $(this).val();
                    FinalVals['material'] = material;
                }
                if(inputName == 'material_type'){
                    var material_type = $(this).val();
                    FinalVals['material_type'] = material_type;
                }
                /*if ($('#customer-type').val() == 'b2b' || $('#gstin').val()){
                    if(inputName == 'gstin'){
                        var GST = $(this).val();
                        if ((GST.length != 15) || (!GSTRegex.test(GST))) {
                            valid = false;
                            $("#"+ $(this).attr("id") +"_error").html("Please enter a valid GSTIN.").show();
                        } else {
                            $("#"+ $(this).attr("id") +"_error").html("").hide();
                            FinalVals['gstin'] = GST
                        }
                    }
                }
                if ($('#customer-type').val() == 'b2b' ||  $('#trade_name').val()){
                    if(inputName == 'trade_name'){
                        var TName = $(this).val();
                        if (TName.length == 0) {
                            valid = false;
                            $("#"+ $(this).attr("id") +"_error").html("Please enter a valid trade name.").show();
                        } else {
                            $("#"+ $(this).attr("id") +"_error").html("").hide();
                            FinalVals['trade_name'] = TName
                        }
                    }
                }*/
            })
            /*$('#click-upload-form textarea:visible').each(function(){ //text area Fields
               var Address = $(this).val();
                if(Address == ""){
                    valid = false;
                    $("#"+ $(this).attr("id") +"_error").html('Please enter your registered address.').show();
                }else {
                    $("#"+ $(this).attr("id") +"_error").html('').hide();
                    FinalVals['address'] = Address
                }
            })*/
            var valid = true;
            //var data = new FormData();
            console.log(FinalVals);
            var isEmptyaudObj = jQuery.isEmptyObject(voiceUploadObj);
            if(isEmptyaudObj === true){
                console.log('No Audio');
            }else{
                FinalVals['audios'] = voiceUploadObj
            }
            var isEmptycamObj = jQuery.isEmptyObject(camUploadObj);
            if(isEmptycamObj === true){
                console.log('No Audio');
            }else{
                FinalVals['cameras'] = camUploadObj
            }
            var isEmptymobObj = jQuery.isEmptyObject(uploadFileAttachmentObj);
            if(isEmptymobObj === true){
                console.log('No Audio');
            }else{
                FinalVals['documents'] = uploadFileAttachmentObj
            }
            if(valid){
                FinalVals['type'] = 'ClickUpload'
                ajax.jsonRpc("/create/enquiry", 'call',FinalVals)
                .then(function (res) {
                    if (res){
						console.log(res);
                        swal("Success!", "Your Enquiry has been placed successfully.", "success").then((ok) => {
                          if (ok) {window.location.href = "/my/enquiries?tab=click";}
                        });
                    }
                    else
                    {
                        swal("OOPS!", `Something went wrong. Please retry.`, "error");
                    }
                });

            }
        },
    });

    // file attachment upload start
    var uploadFileAttachmentObj = {};
    $(function () {
        var dvPreview = $("#attachEnqPreview");
        $("#enq_attachment, #enq_attachment_mobile").change(function () {
            if(typeof (FileReader) != "undefined"){
                var regex = /^([a-zA-Z0-9\s_\\.\-:])+(.jpg|.jpeg|.gif|.png|.bmp)$/;
                $($(this)[0].files).each(function (index) {
                    var file = $(this);
                    var reader = new FileReader();
                    var ext = file[0].name.split('.').pop();
                    var total_size = file[0].size / 1048576;
                    var fileSize = parseFloat(total_size ).toFixed(2);
                    console.log(parseFloat(total_size ).toFixed(2));
                    if(fileSize > 4){
                        swal("OOPS!", `${file[0].name} too Big, Please select file/Image size less than 4 MB.`, "error");
                    }else{
                        reader.onload = function (e) {
                        if(regex.test(file[0].name.toLowerCase())){
                            var divCreate = $("<div class='upl-body-sec'>");
                            var divCreate2 = $("<div class='pull-left left-cont-upl'>");
                            var divCreate3 = $("<div class='pull-right right-cont-upl'>");
                            var divCreate4 = $("<div style='clear:both;'>");
                            var img = $("<img />");
                            img.attr("src", e.target.result);
                            img.attr("id", [file[0].name]+'penq');
                            divCreate2.append(img);
                            var deleteImg = $("<img />");
                            deleteImg.attr("src", '/buildmart/static/src/images/delete.png');
                            deleteImg.attr("class", 'removeAttachMent');
                            deleteImg.attr("id", [file[0].name]+'del');
                            var h4tag = $("<h4></h4>");
                            h4tag.attr("class", [file[0].name]+'penq')
                            h4tag.attr("id", [file[0].name]+'penq')
                            h4tag.text(file[0].name);
                            divCreate2.append(h4tag);
                            var h4tag2 = $("<h4></h4>");
                            h4tag.attr("class", [file[0].name]+'size')
                            h4tag.attr("id", [file[0].name]+'size')
                            var h4B = $("<b></b>");
                            h4B.text(fileSize + ' MB ');
                            h4tag2.text('File Size: ');
                            h4tag2.append(h4B);
                            divCreate3.append(h4tag2);
                            divCreate3.append(deleteImg);
                            divCreate.append(divCreate2);
                            divCreate.append(divCreate3);
                            divCreate.append(divCreate4);
                            dvPreview.append(divCreate);
                            uploadFileAttachmentObj[[file[0].name]] = e.target.result;
                            const isEmpty = Object.keys(uploadFileAttachmentObj).length === 0;
                            if(isEmpty){
                                $("#noImgFile").show();
                            }else{
                                $("#noImgFile").hide();
                            }
                        }else if(ext == "pdf" || ext == "docx" || ext == "doc" || ext == "txt" || ext == "csv" || ext == "xls" || ext == "xlsx"){
                            var divCreate = $("<div class='upl-body-sec'>");
                            var divCreate2 = $("<div class='pull-left left-cont-upl'>");
                            var divCreate3 = $("<div class='pull-right right-cont-upl'>");
                            var divCreate4 = $("<div style='clear:both;'>");

                            var img = $("<img />");
                            img.attr("src", '/buildmart/static/src/images/file.png');
                            img.attr("id", [file[0].name]+'penq');
                            divCreate2.append(img);

                            var deleteImg = $("<img />");
                            deleteImg.attr("src", '/buildmart/static/src/images/delete.png');
                            deleteImg.attr("class", 'removeAttachMent');
                            deleteImg.attr("id", [file[0].name]+'del');

                            var h4tag = $("<h4></h4>");
                            h4tag.attr("class", [file[0].name]+'penq')
                            h4tag.attr("id", [file[0].name]+'penq')
                            h4tag.text(file[0].name);
                            divCreate2.append(h4tag);

                            var h4tag2 = $("<h4></h4>");
                            h4tag.attr("class", [file[0].name]+'size')
                            h4tag.attr("id", [file[0].name]+'size')
                            var h4B = $("<b></b>");
                            h4B.text(fileSize + ' MB ');
                            h4tag2.text('File Size: ');
                            h4tag2.append(h4B);
                            divCreate3.append(h4tag2);
                            divCreate3.append(deleteImg);

                            divCreate.append(divCreate2);
                            divCreate.append(divCreate3);
                            divCreate.append(divCreate4);

                            dvPreview.append(divCreate);
                            uploadFileAttachmentObj[[file[0].name]] = e.target.result;
                            const isEmpty = Object.keys(uploadFileAttachmentObj).length === 0;
                            if(isEmpty){
                                $("#noImgFile").show();
                            }else{
                                $("#noImgFile").hide();
                            }
                        }else{
                            swal("OOPS!", `Uploaded wrong ${file[0].name} file.`, "error");
                        }
                    }
                        reader.readAsDataURL(file[0]);
                    }
                });
            }else {
                swal("OOPS!", "This browser does not support HTML5 FileReader.", "error");
            }
        });
    });
    $(document).on('click', '.removeAttachMent', function(){
        $(this).closest('.upl-body-sec').remove();
        var ID = $(this).attr("id");
        var substringKey = ID.slice(0, -3);
        delete uploadFileAttachmentObj[substringKey];
        const isEmpty = Object.keys(uploadFileAttachmentObj).length === 0;
        if(isEmpty){
            $("#noImgFile").show();
        }else{
            $("#noImgFile").hide();
        }
    });
    // file attachment upload ends

    // camera upload start
    var camUploadObj = {};
    $(function () {
        var dvPreview = $("#cameraEnqPreview");
        $("#enq_camera").change(function () {
            if(typeof (FileReader) != "undefined"){
                var regex = /^([a-zA-Z0-9\s_\\.\-:])+(.jpg|.jpeg|.gif|.png|.bmp)$/;
                $($(this)[0].files).each(function (index) {
                    var file = $(this);
                    var reader = new FileReader();
                    var ext = file[0].name.split('.').pop();
                    var total_size = file[0].size / 1048576;
                    var fileSize = parseFloat(total_size).toFixed(2);
                    console.log(parseFloat(total_size).toFixed(2));
                    if(fileSize > 4){
                        swal("OOPS!", `${file[0].name} too Big, Please select file/Image size less than 4 MB.`, "error");
                    }else{
                        reader.onload = function (e) {
                        if(regex.test(file[0].name.toLowerCase())){
                            var divCreate = $("<div class='upl-body-sec'>");
                            var divCreate2 = $("<div class='pull-left left-cont-upl'>");
                            var divCreate3 = $("<div class='pull-right right-cont-upl'>");
                            var divCreate4 = $("<div style='clear:both;'>");
                            var img = $("<img />");
                            img.attr("src", e.target.result);
                            img.attr("id", [file[0].name]+'penq');
                            divCreate2.append(img);
                            var deleteImg = $("<img />");
                            deleteImg.attr("src", '/buildmart/static/src/images/delete.png');
                            deleteImg.attr("class", 'removeCamAttachMent');
                            deleteImg.attr("id", [file[0].name]+'del');
                            var h4tag = $("<h4></h4>");
                            h4tag.attr("class", [file[0].name]+'penq')
                            h4tag.attr("id", [file[0].name]+'penq')
                            h4tag.text(file[0].name);
                            divCreate2.append(h4tag);
                            var h4tag2 = $("<h4></h4>");
                            h4tag.attr("class", [file[0].name]+'size')
                            h4tag.attr("id", [file[0].name]+'size')
                            var h4B = $("<b></b>");
                            h4B.text(fileSize + ' MB ');
                            h4tag2.text('File Size: ');
                            h4tag2.append(h4B);
                            divCreate3.append(h4tag2);
                            divCreate3.append(deleteImg);
                            divCreate.append(divCreate2);
                            divCreate.append(divCreate3);
                            divCreate.append(divCreate4);
                            dvPreview.append(divCreate);
                            camUploadObj[[file[0].name]] = e.target.result;
                            const isEmpty = Object.keys(camUploadObj).length === 0;
                            if(isEmpty){
                                $("#noCamera").show();
                            }else{
                                $("#noCamera").hide();
                            }
                        }else if(ext == "pdf" || ext == "docx" || ext == "doc" || ext == "txt" || ext == "csv" || ext == "xls" || ext == "xlsx"){
                            var divCreate = $("<div class='upl-body-sec'>");
                            var divCreate2 = $("<div class='pull-left left-cont-upl'>");
                            var divCreate3 = $("<div class='pull-right right-cont-upl'>");
                            var divCreate4 = $("<div style='clear:both;'>");

                            var img = $("<img />");
                            img.attr("src", '/buildmart/static/src/images/file.png');
                            img.attr("id", [file[0].name]+'penq');
                            divCreate2.append(img);

                            var deleteImg = $("<img />");
                            deleteImg.attr("src", '/buildmart/static/src/images/delete.png');
                            deleteImg.attr("class", 'removeCamAttachMent');
                            deleteImg.attr("id", [file[0].name]+'del');

                            var h4tag = $("<h4></h4>");
                            h4tag.attr("class", [file[0].name]+'penq')
                            h4tag.attr("id", [file[0].name]+'penq')
                            h4tag.text(file[0].name);
                            divCreate2.append(h4tag);

                            var h4tag2 = $("<h4></h4>");
                            h4tag.attr("class", [file[0].name]+'size')
                            h4tag.attr("id", [file[0].name]+'size')
                            var h4B = $("<b></b>");
                            h4B.text(fileSize + ' MB ');
                            h4tag2.text('File Size: ');
                            h4tag2.append(h4B);
                            divCreate3.append(h4tag2);
                            divCreate3.append(deleteImg);

                            divCreate.append(divCreate2);
                            divCreate.append(divCreate3);
                            divCreate.append(divCreate4);

                            dvPreview.append(divCreate);
                            camUploadObj[[file[0].name]] = e.target.result;
                            const isEmpty = Object.keys(camUploadObj).length === 0;
                            if(isEmpty){
                                $("#noCamera").show();
                            }else{
                                $("#noCamera").hide();
                            }
                        }else{
                            swal("OOPS!", `Uploaded wrong ${file[0].name} file.`, "error");
                        }
                    }
                        reader.readAsDataURL(file[0]);
                    }
                });
            }else {
                swal("OOPS!", "This browser does not support HTML5 FileReader.", "error");
            }
        });
    });
    $(document).on('click', '.removeCamAttachMent', function(){
        $(this).closest('.upl-body-sec').remove();
        var ID = $(this).attr("id");
        var substringKey = ID.slice(0, -3);
        delete camUploadObj[substringKey];
        const isEmpty = Object.keys(camUploadObj).length === 0;
        if(isEmpty){
            $("#noCamera").show();
        }else{
            $("#noCamera").hide();
        }
    });
    // camera upload ends

    // tab shift code start
    $('#cam_upload').click(function(){
        $("#cameraEnqPreview").show();
        $(this).addClass('active-click');
        $("#voiceEnqPreview").hide();
        $('#voice_upload').removeClass('active-click');
        $("#attachEnqPreview").hide();
        $('#file_upload').removeClass('active-click');
    });
    $('#voice_upload').click(function(){
        $("#cameraEnqPreview").hide();
        $('#cam_upload').removeClass('active-click');
        $("#voiceEnqPreview").show();
        $(this).addClass('active-click');
        $("#attachEnqPreview").hide();
        $('#file_upload').removeClass('active-click');
    });
    $('#file_upload').click(function(){
        $("#cameraEnqPreview").hide();
        $('#cam_upload').removeClass('active-click');
        $("#voiceEnqPreview").hide();
        $('#voice_upload').removeClass('active-click');
        $("#attachEnqPreview").show();
        $(this).addClass('active-click');
    });


    // upload document for price enq
   var uploadEnquiryObj = {};
    $(function () {
        var dvPreview = $("#priceEnqPreview");
        dvPreview.html("");
        $("#enq_attachment").change(function () {
            if (typeof (FileReader) != "undefined") {
                var regex = /^([a-zA-Z0-9\s_\\.\-:])+(.jpg|.jpeg|.gif|.png|.bmp)$/;
               $($(this)[0].files).each(function (index) {
                    var file = $(this);
                    var reader = new FileReader();
                    var ext = file[0].name.split('.').pop();
                    var total_size = file[0].size / 1048576;
                    var fileSize = parseFloat(total_size).toFixed(2);
                    console.log(parseFloat(total_size).toFixed(2));
                    if(fileSize > 4) {
                        swal("OOPS!", `${file[0].name} too Big, Please select file/Image size less than 4 MB.`, "error");
                    }else{
                        reader.onload = function (e) {
                        if(regex.test(file[0].name.toLowerCase())){
                            var divCreate = $("<div class='imgRepeatDiv'><img src='https://cdn3.iconfinder.com/data/icons/faticons/32/remove-01-512.png' class='removeIcon'/>");
                            var img = $("<img />");
                            img.attr("style", "height:60px;width: 60px;float:left;margin-right:5px;border:1px solid #ddd;margin-bottom: 5px;");
                            img.attr("src", e.target.result);
                            img.attr("class", [file[0].name]+'penq', 'dynamicContent')
                            img.attr("id", [file[0].name]+'penq')
                            divCreate.append(img)
                            dvPreview.append(divCreate);
                            uploadEnquiryObj[[file[0].name]] = e.target.result;
                            $("#enquiry_attachment_error").html("").hide();
                        }else if(ext == "pdf" || ext == "docx" || ext == "doc" || ext == "txt" || ext == "csv" || ext == "xls" || ext == "xlsx"){
                            var divCreate = $("<div class='imgRepeatDiv'><img src='https://cdn3.iconfinder.com/data/icons/faticons/32/remove-01-512.png' class='removeIcon'/>");
                            var pTag = $("<p></p>");
                            pTag.attr("style", "float:left;margin-right:5px;border: 1px solid #ddd;padding: 5px;height: 60px;margin-bottom: 5px;line-height: 40px;font-family:Lato-Regular;overflow: hidden;white-space: nowrap;text-overflow: ellipsis;max-width: 200px;");
                            pTag.attr("class", [file[0].name]+'penq')
                            pTag.attr("id", [file[0].name]+'penq')
                            pTag.text(file[0].name);
                            divCreate.append(pTag)
                            dvPreview.append(divCreate);
                            uploadEnquiryObj[[file[0].name]] = e.target.result;
                            $("#enquiry_attachment_error").html("").hide();
                        }else{
                            swal("OOPS!", `Uploaded wrong ${file[0].name} file.`, "error");
                        }
                    }
                        reader.readAsDataURL(file[0]);
                    }
                });
            } else {
                swal("OOPS!", "This browser does not support HTML5 FileReader.", "error");
            }
            setTimeout(function(){
                removeDuplicates();
            },100)
        });
        function removeDuplicates(){
            $('#priceEnqPreview img').each(function () {
                $('[id="' + this.id + '"]:gt(0)').remove();
            });
            $('#priceEnqPreview p').each(function () {
               $('[id="' + this.id + '"]:gt(0)').remove();
            });
            $("#priceEnqPreview .imgRepeatDiv").map(function() {
               if(this.children.length === 1){
                    $(this).remove();
                }
            })
       }
    });
//    $(document).on('click', '.removeIcon', function(){
//        var ID = $(this).next().attr("id");
//        var substringKey = ID.slice(0, -4);
//        $(this).next().remove();
//        $(this).remove();
//        delete uploadEnquiryObj[substringKey];
//    });
//    // upload document for price enq
//
//    // upload document for Delivery Address
//    var uploadDeliveryObj = {};
//    $(function () {
//        var dvPreview = $("#deliveryAddressPreview");
//        dvPreview.html("");
//        $("#delivery_attachment").change(function () {
//            if (typeof (FileReader) != "undefined") {
//                var regex = /^([a-zA-Z0-9\s_\\.\-:])+(.jpg|.jpeg|.gif|.png|.bmp)$/;
//                $($(this)[0].files).each(function (index) {
//                    var file = $(this);
//                    var reader = new FileReader();
//                    var ext = file[0].name.split('.').pop();
//                    var fileSize = parseFloat(file[0].size / (1024 * 1024)).toFixed(2);
//                    if(fileSize > 4) {
//                        swal("OOPS!", `${file[0].name} too Big, Please select file/Image size less than 4 MB.`, "error");
//                    }else{
//                        reader.onload = function (e) {
//                        if(regex.test(file[0].name.toLowerCase())){
//                            var divCreate = $("<div class='imgRepeatDiv'><img src='https://cdn3.iconfinder.com/data/icons/faticons/32/remove-01-512.png' class='removeIconDel'/>");
//                            var img = $("<img />");
//                            img.attr("style", "height:60px;width: 60px;float:left;margin-right:5px;border:1px solid #ddd;margin-bottom: 5px;");
//                            img.attr("src", e.target.result);
//                            img.attr("class", [file[0].name]+'del')
//                            img.attr("id", [file[0].name]+'del')
//                            divCreate.append(img)
//                            dvPreview.append(divCreate);
//                            uploadDeliveryObj[[file[0].name]] = e.target.result;
//                            $("#delivery_attachment_error").html("").hide();
//                        }else if(ext == "pdf" || ext == "docx" || ext == "doc" || ext == "txt" || ext == "csv" || ext == "xls" || ext == "xlsx"){
//                            var divCreate = $("<div class='imgRepeatDiv'><img src='https://cdn3.iconfinder.com/data/icons/faticons/32/remove-01-512.png' class='removeIconDel'/>");
//                            var pTag = $("<p></p>");
//                            pTag.attr("style", "float:left;margin-right:5px;border: 1px solid #ddd;padding: 5px;height: 60px;margin-bottom: 5px;line-height: 40px;font-family:Lato-Regular;overflow: hidden;white-space: nowrap;text-overflow: ellipsis;max-width: 200px;");
//                            pTag.attr("class", [file[0].name]+'del')
//                            pTag.attr("id", [file[0].name]+'del')
//                            pTag.text(file[0].name);
//                            divCreate.append(pTag)
//                            dvPreview.append(divCreate);
//                            uploadDeliveryObj[[file[0].name]] = e.target.result;
//                            $("#delivery_attachment_error").html("").hide();
//                        }else{
//                            swal("OOPS!", `Uploaded wrong ${file[0].name} file.`, "error");
//                        }
//                    }
//                        reader.readAsDataURL(file[0]);
//                    }
//
//                });
//            } else {
//                swal("OOPS!", "This browser does not support HTML5 FileReader.", "error");
//            }
//            setTimeout(function(){
//                removeDuplicatesDel();
//            },100)
//        });
//        function removeDuplicatesDel(){
//            $('#deliveryAddressPreview img').each(function () {
//                $('[id="' + this.id + '"]:gt(0)').remove();
//            });
//            $('#deliveryAddressPreview p').each(function () {
//                $('[id="' + this.id + '"]:gt(0)').remove();
//            });
//            $("#deliveryAddressPreview .imgRepeatDiv").map(function() {
//                if(this.children.length === 1){
//                    $(this).remove();
//                }
//            })
//        }
//        $(document).on('click', '.removeIconDel', function(){
//            var ID = $(this).next().attr("id");
//            var substringKey = ID.slice(0, -3);
//            $(this).next().remove();
//            $(this).remove();
//            delete uploadDeliveryObj[substringKey];
//        });
//    });
    // click & upload --- ends

   /* Contact us page --- starts */
   $('.input-name-cont').keyup(function() {
        if($(".input-name-cont").val() == ""){
            $('#error_name_cont').html('Please enter your name.').show();
        }else{
            $("#error_name_cont").html("").hide();
        }
   });
   $('.input-email-cont').keyup(function() {
        var EmailRegex = /^([A-Za-z0-9_\-\.])+\@([A-Za-z0-9_\-\.])+\.([A-Za-z]{2,4})$/;
        if($(".input-email-cont").val() == ""){
            $('#error_email_cont').html('Please enter your email.').show();
        }else if(EmailRegex.test($(".input-email-cont").val()) == false){
            $("#error_email_cont").html("Please enter valid email address.").show();
        }else{
            $("#error_email_cont").html("").hide();
        }
   });
   $('.input-phone-cont').keyup(function() {
        var MobileRegex = /^\d*[0-9-+](|.\d*[0-9-+]|,\d*[0-9-+])?$/;
        if($('.input-phone-cont').val() == ""){
            $('#error_phone_cont').html('Please enter your mobile number.').show();
        }else if(!MobileRegex.test($('.input-phone-cont').val()) || ($('.input-phone-cont').val().length < 10)){
            $("#error_phone_cont").html("Please enter valid mobile number.").show();
        }else{
            $("#error_phone_cont").html("").hide();
        }
   });
   $('#bs-contact-us').click(function(){
        var valid = true

        var EmailRegex = /^([A-Za-z0-9_\-\.])+\@([A-Za-z0-9_\-\.])+\.([A-Za-z]{2,4})$/;
        if($(".input-name-cont").val() == ""){
            $('#error_name_cont').html('Please enter your name.').show();
            valid = false;
        }else{
            $("#error_name_cont").html("").hide();
        }

        if($(".input-email-cont").val() == ""){
            $('#error_email_cont').html('Please enter your email.').show();
            valid = false;
        }else if(EmailRegex.test($(".input-email-cont").val()) == false){
            valid = false;
            $("#error_email_cont").html("Please enter valid email address.").show();
        }else{
            $("#error_email_cont").html("").hide();
        }

        var MobileRegex = /^\d*[0-9-+](|.\d*[0-9-+]|,\d*[0-9-+])?$/;
        if($('.input-phone-cont').val() == ""){
            $('#error_phone_cont').html('Please enter your mobile number.').show();
            valid = false;
        }else if(!MobileRegex.test($('.input-phone-cont').val()) || ($('.input-phone-cont').val().length < 10)){
            $("#error_phone_cont").html("Please enter valid mobile number.").show();
            valid = false;
        }else{
            $("#error_phone_cont").html("").hide();
        }

        var FinalVals = {'contact_name': $('#your-name').val(),
                    'phone': $('#phone-number').val(),
                    'email_from': $('#email').val(),
                    'partner_name': $('#company').val(),
                    'name': $('#subject').val(),
                    'description': $('#question').val()
                    }
        if (valid){
            ajax.jsonRpc('/bs/contactus',"call", FinalVals).then(function(result){
                if (result != false){
                    swal("Success!", "Your contact has been sent successfully. We will get back to you shortly.", "success").then((ok) => {
                      if (ok) {location.reload();}
                    });
                }
                else{
                    swal("OOPS!", `Something went wrong.`, "error");
                }
            });
        }
   });
   /* Contact us page --- ends */
   /* BS enquiry multi select starts */
    var onSelector = {
        get: function (selector) {
            var ele = document.querySelectorAll(selector);
            for (var i = 0; i < ele.length; i++) {
                this.init(ele[i]);
            }
            return ele;
        },
        template: function (html) {
            var template = document.createElement('div');
            template.innerHTML = html.trim();
            return this.init(template.childNodes[0]);
        },
        init: function (ele) {
            ele.on = function (event, func) {
                this.addEventListener(event, func);
            }
            return ele;
        }
    };
    function drop (info) {
        var o = {
            options: info.options,
            selected: info.selected || [],
            preselected: info.preselected || [],
            open: false,
            html: {
                select: onSelector.get(info.selector)[0],
                options: onSelector.get(info.selector + ' option'),
                parent: undefined,
            },
            init: function () {
                if (typeof(onSelector.get(info.selector)[0]) !== 'undefined'){
                    this.html.parent = onSelector.get(info.selector)[0].parentNode
                    this.html.drop = onSelector.template('<div class="drop"></div>')
                    this.html.dropDisplay = onSelector.template('<div class="drop-display" id="display-'+$(onSelector.get(info.selector)[0]).attr('id') +'">Display</div>')
                    this.html.dropOptions = onSelector.template('<div class="drop-options">Options</div>')
                    this.html.dropScreen = onSelector.template('<div class="drop-screen"></div>')
                    this.html.parent.insertBefore(this.html.drop, this.html.select)
                    this.html.drop.appendChild(this.html.dropDisplay)
                    this.html.drop.appendChild(this.html.dropOptions)
                    this.html.drop.appendChild(this.html.dropScreen)
                    this.html.drop.appendChild(this.html.select);
                    var that = this;
                    this.html.dropDisplay.on('click', function () {
                        that.toggle()
                    });
                    this.html.dropScreen.on('click', function () {
                        that.toggle()
                    });
                    this.load()
                    this.preselect()
                    this.render();
                }
            },
            toggle: function () {
                this.html.drop.classList.toggle('open');
            },
            addOption: function (e, element) {
                var index = Number(element.dataset.index);
                this.clearStates()
                this.selected.push({
                    index: Number(index),
                    state: 'add',
                    removed: false
                })
                this.options[index].state = 'remove';
                this.render()
            },
            removeOption: function (e, element) {
                e.stopPropagation();
                this.clearStates()
                var index = Number(element.dataset.index);
                this.selected.forEach(function (select) {
                    if (select.index == index && !select.removed) {
                        select.removed = true
                        select.state = 'remove'
                    }
                })
                this.options[index].state = 'add'
                this.render();
            },
            load: function () {
                this.options = [];
                for (var i = 0; i < this.html.options.length; i++) {
                    var option = this.html.options[i]
                    this.options[i] = {
                        html: option.innerHTML,
                        value: option.value,
                        selected: option.selected,
                        state: '',
                        id : $(option).attr("id"),
                    }
                }
            },
            preselect: function () {
                var that = this;
                this.selected = [];
                this.preselected.forEach(function (pre) {
                    that.selected.push({
                        index: pre,
                        state: 'add',
                        removed: false
                    })
                    that.options[pre].state = 'remove';
                })
            },
            render: function () {
                this.renderDrop()
                this.renderOptions()
            },
            renderDrop: function () {
                var that = this;
                var parentHTML = onSelector.template('<div></div>')
                this.selected.forEach(function (select, index) {
                    var option = that.options[select.index];
                    var childHTML = onSelector.template('<span class="item ' + select.state  + '" id="'+ option.id +  '">' + option.html + '</span>')
                    var childCloseHTML = onSelector.template('<i class="btnclose" data-index="' + select.index + '"></i></span>')
                    childCloseHTML.on('click', function (e) {
                        that.removeOption(e, this)
                    })
                    childHTML.appendChild(childCloseHTML)
                    parentHTML.appendChild(childHTML)
                })
                this.html.dropDisplay.innerHTML = '';
                this.html.dropDisplay.appendChild(parentHTML)
            },
            renderOptions: function () {
                var that = this;
                var parentHTML = onSelector.template('<div></div>')
                this.options.forEach(function (option, index) {
                    var childHTML = onSelector.template('<a data-index="' + index + '" class="' + option.state + '" id="'+ option.id + '" >' + option.html + '</a>')
                    childHTML.on('click', function (e) {
                        that.addOption(e, this)
                    })
                    parentHTML.appendChild(childHTML)
                })
                this.html.dropOptions.innerHTML = '';
                this.html.dropOptions.appendChild(parentHTML)
            },
            clearStates: function () {
                var that = this;
                this.selected.forEach(function (select, index) {
                    select.state = that.changeState(select.state)
                })
                this.options.forEach(function (option) {
                    option.state = that.changeState(option.state)
                })
            },
            changeState: function (state) {
                switch (state) {
                    case 'remove':
                        return 'hide'
                    case 'hide':
                        return 'hide'
                    default:
                        return ''
                }
            },
            isSelected: function (index) {
                var check = false
                this.selected.forEach(function (select) {
                    if (select.index == index && select.removed == false) check = true
                })
                return check
            }
        };
        o.init();
        return o;
    }
    drop({
        selector: '.leave-enquiry #EnquiryLocation',
    //	preselected: [0,3]
      });
    drop({
    selector: '.leave-enquiry #EnqBrands',
    //	preselected: [0, 2]
    });
    drop({
    selector: '.leave-enquiry #categories',
    //	preselected: [0,3]
    });
    drop({
        selector: '.leave-enquiry #subcategories',
    //	preselected: [0, 2]
      });
    /* BS enquiry multi select ends */

    /* Portal - BS enquiry starts */
    $('.leave-enquiry .drop-display#display-EnquiryLocation').bind("DOMSubtreeModified",function(){
        if ($('#display-EnquiryLocation span:not(.remove,.hide)').length > 0){$('#states-error').hide()}
        else{$('#states-error').show()}
    })
    $('.leave-enquiry .drop-display#display-categories').bind("DOMSubtreeModified",function(){
        if ($('#display-categories span:not(.remove,.hide)').length > 0){$('#categories-error').hide()}
        else{$('#categories-error').show()}
    })
    $('.leave-enquiry .drop-display#display-subcategories').bind("DOMSubtreeModified",function(){
        if ($('#display-subcategories span:not(.remove,.hide)').length > 0){$('#subcategories-error').hide()}
        else{$('#subcategories-error').show()}
    })
    $('.leave-enquiry .drop-display#display-EnqBrands').bind("DOMSubtreeModified",function(){
        if ($('#display-EnqBrands span:not(.remove,.hide)').length > 0){$('#brands-error').hide()}
        else{$('#brands-error').show()}
    })

    var States = [], categories = [], subcategories = [], EnqBrands = []
    $( ".bs-enquiry-submit" ).click(function( event ) {
        $('.leave-enquiry .drop-display#display-EnquiryLocation span').each(function(){
            States.push($(this).attr('id'))
        })
        $('.leave-enquiry .drop-display#display-categories span').each(function(){
            categories.push($(this).attr('id'))
        })
        $('.leave-enquiry .drop-display#display-subcategories span').each(function(){
            subcategories.push($(this).attr('id'))
        })
        $('.leave-enquiry .drop-display#display-EnqBrands span').each(function(){
            EnqBrands.push($(this).attr('id'))
        })
        if($('#materialQN').val() == ""){
            $("#materialQN-error").html('Please enter material quantity.').show();
        }else {
            $("#materialQN-error").html('').hide();
        }
        if (States.length == 0 || categories.length == 0 || subcategories.length == 0 || EnqBrands.length == 0){
            if (States.length == 0){$('span#states-error').html('Please select location(s).')}
            else{$('span#states-error').html('')}

            if (categories.length == 0){$('span#categories-error').html('Please select type(s).')}
            else{$('span#categories-error').html('')}

            if (subcategories.length == 0){$('span#subcategories-error').html('Please select subtype(s).')}
            else{$('span#subcategories-error').html('')}

            if (EnqBrands.length == 0){$('span#brands-error').html('Please select brand(s).')}
            else{$('span#brands-error').html('')}
        }
        else{
            $("#materialQN-error").html('').hide();
            $('span#states-error').html('')
            $('span#categories-error').html('')
            $('span#subcategories-error').html('')
            $('span#brands-error').html('')
            ajax.jsonRpc("/create/enquiry", 'call',{
                'type': 'PriceEnquiry',
                'location_ids': States,
                'quantity': parseInt($('.leave-enquiry #materialQN').val()),
                'brand_ids':EnqBrands,
                'ecomm_subcateg_ids':subcategories,
                'ecomm_category_ids':categories,
                'uom_id': parseInt($('.leave-enquiry #uom option:selected').attr('id')),
                'material_description': $.trim($(".leave-enquiry #description").val()),
                'partner_id': parseInt($('#partner-id').val()),
                })
                .then(function (res) {
                    if (res){
                        swal("Success!", "Enquiry has been successfully submitted.", "success").then((ok) => {
                          if (ok) {window.location = '/my/enquiries?tab=enquiry'}
                        });
                    }
                    else{
                        swal("OOPS!", `Please recheck values.`, "error");
                    }
            })
        }
    });
    /* Portal - BS enquiry ends */
    // modal images show while click on image
    var popupModalShow = document.getElementById("popupModalShow");
    var showImg;
    var modalImg = document.getElementById("modalImg");
    $('.imageShowClick').click(function(){
        var id = $(this).attr('id');
        showImg = document.getElementById(id);
        popupModalShow.style.display = "block";
        modalImg.src = this.src;
    })
    var closeModal = document.getElementsByClassName("close-modal")[0];
    if(closeModal != null || closeModal != undefined){
        closeModal.onclick = function() {
          popupModalShow.style.display = "none";
        }
    }
    // modal images show while click on image
    // Login & Security : change password confirm password validations start
    $(".password-eye-icon").click(function(){
        var elmId = $(this).attr("id").substring(3);
        var img = document.getElementById($(this).attr("id")).src;
        if (img.indexOf('eye-slash.png')!=-1) {
            document.getElementById($(this).attr("id")).src  = '/buildmart/static/src/images/eye.png';
        }else{
           document.getElementById($(this).attr("id")).src = '/buildmart/static/src/images/eye-slash.png';
        }
        var showPasswordInput = document.getElementById(elmId);
        if (showPasswordInput.type === "password") {
            showPasswordInput.type = "text";
        } else {
            showPasswordInput.type = "password";
        }
    });
    $("#changePassword").click(function(){
        $("#showChangePassword").show();
        $(this).hide();
    });
    $("#cancelChangePassword").click(function(){
        $("#showChangePassword").hide();
        $("#changePassword").show();
    });

    var validatePasswordCheck = true;
    $('.card-login-sequrity .submit-password-btn').click(function(e){
        validatePasswordCheck = true;
        PasswordCurrentCheckLength();
        PasswordNewCheckLength();
        checkPasswordMatch();
        if(validatePasswordCheck){
                    ajax.jsonRpc('/change/password',"call", {'CurrentPassword': $('.card-login-sequrity #currentPassword').val(),
                                                    'NewPassword': $('.card-login-sequrity #newPassword').val(),
                                                    'ConfirmPassword': $('.card-login-sequrity #confirmPassword').val()
            }).then(function(result){
               if (result){
                swal("Success!", "Successfully changed the password!", "success").then((ok) => {
                  if (ok) {location.reload()}
                });
               }
               else{
                swal("Error!", "Incorrect current password!", "error");
               }
            })
        }
    })

    $(".card-login-sequrity #currentPassword").keyup(PasswordCurrentCheckLength);
    function PasswordCurrentCheckLength(){
        var passwordLength = $(".card-login-sequrity #currentPassword").val();
        if(passwordLength == ""){
            $('#error_currentPassword').html('Please enter current password.').show();
            validatePasswordCheck = false;
        }else {
            $('#error_currentPassword').html('').hide();
        }
    }
    $(".card-login-sequrity #newPassword").keyup(PasswordNewCheckLength);
    function PasswordNewCheckLength(){
        var passwordLength = $(".card-login-sequrity #newPassword").val();
        if(passwordLength == ""){
            $('#error_newPassword').html('Please enter new password.').show();
            validatePasswordCheck = false;
        }else if(passwordLength.length < 6){
            $('#error_newPassword').html('You have to enter at least 6 characters.').show();
            validatePasswordCheck = false;
        }else {
            $('#error_newPassword').html('').hide();
        }
    }
    $(".card-login-sequrity #confirmPassword").keyup(checkPasswordMatch);
    function checkPasswordMatch() {
        $(".signupIndCustomer #error_CheckPasswordMatch").html("");
        PasswordNewCheckLength();
        var confirm_password = $('.card-login-sequrity #confirmPassword').val();
        var password = $(".card-login-sequrity #newPassword").val();
        if(confirm_password == ""){
            $("#error_CheckPasswordMatch").html("Please enter confirm password.");
            validatePasswordCheck = false;
        }else if (password != confirm_password) {
            $("#error_CheckPasswordMatch").html("Passwords does not match!");
            validatePasswordCheck = false;
        }
        else {
            $("#error_CheckPasswordMatch").html("");
        }
    }
    // change password confirm password validations ends

        // Add address modal validations start
    $(document).on("click", ".submitAddressForm", function(event){
        let name = document.forms["validateAddressForm"]["name"].value;
        let Mobile = document.forms["validateAddressForm"]["mobile"].value;
        let address = document.forms["validateAddressForm"]["street"].value;
        let site_name = document.forms["validateAddressForm"]["site_name"].value;
        let landmark = document.forms["validateAddressForm"]["landmark"].value;
        let city = document.forms["validateAddressForm"]["city"].value;
        let zip = document.forms["validateAddressForm"]["zip"].value;
        var validAddressForm = true;
        var FinalVals = {'name':name, 'mobile':Mobile, 'street':address,'street2':$('#inputAddress2').val(),
                        'site_name':site_name, 'landmark':landmark,'city':city, 'zip':zip,
                        'type':$('#validateAddressForm').attr('address-type')}
        if(name == ''){
            $("#error_inputEmail4").html("Please enter valid contact name.").show();
            validAddressForm = false;
        }else{
            $("#error_inputEmail4").html("").hide();
        }
        if ($("#inputState").val() == 0){
            $("#state_error").html("Please select state.").show();
            validAddressForm = false;
        }else{
            FinalVals['state_id'] = parseInt($("#inputState").val());
            $("#state_error").html("").hide();
        }

        if ($("#district_id").val() == 0){
            $("#district_error").html("Please select district.").show();
            validAddressForm = false;
        }else{
            FinalVals['district_id'] = parseInt($("#district_id").val());
            $("#district_error").html("").hide();
        }

        var AllNumericRegex= /^[0-9]+$/;
        if(zip == ""){
            $("#zip_error").html('Please enter your pincode.').show();
            validAddressForm = false;
        }else if((zip.length < 6) || (!AllNumericRegex.test(zip))){
            $("#zip_error").html("Please enter a valid pincode.").show();
            validAddressForm = false;
        }else {
            $("#zip_error").html('').hide();
        }

        if(address == ''){
            $("#address_error").html("Please enter valid address.").show();
            validAddressForm = false;
        }else{
            $("#address_error").html("").hide();
        }

        if(site_name == ''){
            $("#site_name_error").html("Please enter valid site name.").show();
            validAddressForm = false;
        }else{
            $("#site_name_error").html("").hide();
        }

        if(landmark == ''){
            $("#landmark_error").html("Please enter valid land mark.").show();
            validAddressForm = false;
        }else{
            $("#landmark_error").html("").hide();
        }

        if(city == ''){
            $("#city_error").html("Please enter valid city.").show();
            validAddressForm = false;
        }else{
            $("#city_error").html("").hide();
        }

        var MobileRegex = /^\d*[0-9-+](|.\d*[0-9-+]|,\d*[0-9-+])?$/;
        if(Mobile == ""){
            $('#mobile_error').html('Please enter your mobile number.').show();
            validAddressForm = false;
        }else if(!MobileRegex.test(Mobile) || (Mobile.length < 10)){
            $("#mobile_error").html("Please enter valid mobile number.").show();
            validAddressForm = false;
        }else{
            $("#mobile_error").html("").hide();
        }

        if(!validAddressForm){
           return false;
        }else{
            if ($(this).attr('address-id') != false){
                FinalVals['address-id'] = $('#validateAddressForm').attr('address-id')
                ajax.jsonRpc('/edit/address',"call", FinalVals).then(function(result){
                    if (result != false){
                        swal("Success!", "Address modified successfully!", "success").then((ok) => {
                          if (ok) {
                            $("#PortalModifyAddress").hide();
                            window.location ='/my/address/?tab='+result;
                          }
                        });
                    }
                    else{swal("OOPS!", `Something went wrong.`, "error");}
                })
            }
            else{
                 ajax.jsonRpc('/add/address',"call", FinalVals).then(function(result){
                    if (result != false){
                        swal("Success!", "Address successfully created!", "success").then((ok) => {
                          if (ok) {
                            $("#PortalModifyAddress").hide();
                            window.location ='/my/address/?tab='+result;
                           }
                        });
                    }
                    else{swal("OOPS!", `Something went wrong.`, "error");}
                })
            }
        }
    });

    $(document).on('keyup', '#inputEmail4', function(e) {
      if(e.target.value == ''){
        $("#error_inputEmail4").html("Please enter valid contact name.").show();
      }else{
        $("#error_inputEmail4").html("").hide();
      }
    });

    $(document).on('keyup', '#inputPassword4', function(e) {
      var MobileRegex = /^\d*[0-9-+](|.\d*[0-9-+]|,\d*[0-9-+])?$/;
        if(e.target.value == ""){
            $('#mobile_error').html('Please enter your mobile number.').show();
        }else if(!MobileRegex.test(e.target.value) || (e.target.value.length < 10)){
            $("#mobile_error").html("Please enter valid mobile number.").show();
        }else{
            $("#mobile_error").html("").hide();
        }
    });

    $(document).on('keyup', '#inputAddress', function(e) {
      if(e.target.value == ''){
            $("#address_error").html("Please enter valid address.").show();
        }else{
            $("#address_error").html("").hide();
        }
    });


    $(document).on('keyup', '#inputSitename', function(e) {
      if(e.target.value == ''){
            $("#site_name_error").html("Please enter valid site name.").show();
        }else{
            $("#site_name_error").html("").hide();
        }
    });

    $(document).on('keyup', '#inputlandmark', function(e) {
      if(e.target.value == ''){
            $("#landmark_error").html("Please enter valid land mark.").show();
        }else{
            $("#landmark_error").html("").hide();
        }
    });

    $(document).on('keyup', '#inputCity', function(e) {
      if(e.target.value == ''){
            $("#city_error").html("Please enter valid city.").show();
        }else{
            $("#city_error").html("").hide();
        }
    });

    $(document).on('change', '#inputState', function(e) {
      if (e.target.value == 0){
            $("#state_error").html("Please select state.").show();
        }else{
            $("#state_error").html("").hide();
        }
    });

    $(document).on('change', '#district_id', function(e) {
      if (e.target.value == 0){
            $("#district_error").html("Please select state.").show();
        }else{
            $("#district_error").html("").hide();
        }
    });

    $(document).on('keyup', '#inputZip', function(e) {
      var AllNumericRegex= /^[0-9]+$/;
        if(e.target.value == ""){
            $("#zip_error").html('Please enter your pincode.').show();
        }else if((e.target.value.length < 6) || (!AllNumericRegex.test(e.target.value))){
            $("#zip_error").html("Please enter a valid pincode.").show();
        }else {
            $("#zip_error").html('').hide();
        }
    });
    $("#delAddressModel").click(function () {
        $("#inlineRadio2").prop("checked", true);
    });
    $("#bilAddressModel").click(function () {
        $("#inlineRadio1").prop("checked", true);
    });
    // Add address modal validations ends
     /* Add bank modal starts */
        $('#bank-details #delete_bank').click(function(){
            swal({
              title: "Are you sure want to delete it?",
              text: "Once deleted, you will not be able to recover this bank details!",
              icon: "warning",
              buttons: true,
              dangerMode: true,
            })
            .then((willDelete) => {
              if (willDelete) {
                    rpc.query({
                        model: 'res.partner.bank',
                        method: 'unlink',
                        args: [parseInt($(this).attr('partner-bank-id'))],
                    }).then(function(){
                        swal("Success!", "Successfully deleted!", "success").then(function(){
                            window.location.href = "/my/banks?tab=others";
                        });
                    });
              } else {
                swal("Bank details are not deleted!");
              }
            });
        })

        $('#modal_bank_details #bank_attachment').change(encodeImageFileAsURL(function(base64Img){
            $('#modal_bank_details #bank_attachment_base64').val(base64Img.replace(/^data:.+;base64,/, ''));
            //.css('background-image', 'url('+base64Img +')').hide().fadeIn(650);
        }));

        $('#modal_bank_details #acc_holder_name').change(function(){
            if (!$(this).val()){$('#modal_bank_details #acc_holder_name_error').html('Please enter beneficiary name.').show()}
            else{$('#modal_bank_details #acc_holder_name_error').hide()}
        })
        $('#modal_bank_details #acc_no').change(function(){
            if (!$(this).val()){$('#modal_bank_details #acc_no_error').html('Please enter account number.').show()}
            else if (!$.isNumeric($(this).val())){$('#modal_bank_details #acc_no_error').html('Please enter valid account number.').show()}
            else{$('#modal_bank_details #acc_no_error').hide()}
        })
        $('#modal_bank_details #confirm_acc_no').change(function(){
            if (!$(this).val()){$('#modal_bank_details #confirm_acc_no_error').html('Please enter confirm account number.').show()}
            else if (!$.isNumeric($(this).val())){$('#modal_bank_details #acc_no_error').html('Please enter valid account number.').show()}
            else if ($('#modal_bank_details #acc_no').val() != $(this).val()){$('#modal_bank_details #confirm_acc_no_error').html('Account number mismatch.').show()}
            else{$('#modal_bank_details #confirm_acc_no_error').hide()}
        })
        $('#modal_bank_details #bank_name').change(function(){
            if (!$(this).val()){$('#modal_bank_details #bank_name_error').html('Please enter bank name.').show()}
            else{$('#modal_bank_details #bank_name_error').hide()}
        })
        $('#modal_bank_details #ifsc_code').change(function(){
            if (!$(this).val()){$('#modal_bank_details #ifsc_code_error').html('Please enter IFSC code.').show()}
            else{$('#modal_bank_details #ifsc_code_error').hide()}
        })
        $('#modal_bank_details #bank_address').change(function(){
            if (!$(this).val()){$('#modal_bank_details #bank_address_error').html('Please enter bank address.').show()}
            else{$('#modal_bank_details #bank_address_error').hide()}
        })
        $('#modal_bank_details #bank_attachment').change(function(){
            if (!$(this).val()){$('#modal_bank_details #bank_attachment_error').html('Please attach required document.').show()}
            else{$('#modal_bank_details #bank_attachment_error').hide()}
        })

        $('#modal_bank_details #add_bank').click(function(){
            var BankDetails = {'is_default': $('#modal_bank_details #is_default').is(':checked')}
            var valid = true
            if ($('#modal_bank_details #acc_holder_name').val()){BankDetails['acc_holder_name']=$('#modal_bank_details #acc_holder_name').val()}
            else{valid=false;$('#modal_bank_details #acc_holder_name_error').html('Please enter beneficiary name.').show()}

            if ($('#modal_bank_details #acc_no').val()){BankDetails['acc_number']=$('#modal_bank_details #acc_no').val()}
            else{valid=false;$('#modal_bank_details #acc_no_error').html('Please enter account number.').show()}

            if (!($('#modal_bank_details #confirm_acc_no').val() && $('#modal_bank_details #acc_no').val() == $('#modal_bank_details #confirm_acc_no').val()))
                {valid=false;$('#modal_bank_details #confirm_acc_no_error').html('Please enter confirm account number.').show()}

            if ($('#modal_bank_details #bank_name').val()){BankDetails['bank_name']=$('#modal_bank_details #bank_name').val()}
            else{valid=false;$('#modal_bank_details #bank_name_error').html('Please enter bank name.').show()}

            if ($('#modal_bank_details #ifsc_code').val()){BankDetails['ifsc_code']=$('#modal_bank_details #ifsc_code').val()}
            else{valid=false;$('#modal_bank_details #ifsc_code_error').html('Please enter IFSC code.').show()}

            if ($('#modal_bank_details #bank_address').val()){BankDetails['bank_address']=$('#modal_bank_details #bank_address').val()}
            else{valid=false;$('#modal_bank_details #bank_address_error').html('Please enter bank address.').show()}

            if ($('#modal_bank_details #bank_attachment').val()){
                BankDetails['bank_attachment_name']=$('#modal_bank_details #bank_attachment').val()
                BankDetails['bank_attachment_base64']=$('#modal_bank_details #bank_attachment_base64').val()
            }
            else{valid=false;$('#modal_bank_details #bank_attachment_error').html('Please attach required document.').show()}

            if (! $('#modal_bank_details #agree_terms').is(":checked")){valid=false;}

            if (valid){
                ajax.jsonRpc('/bank/add',"call", BankDetails).then(function(result){
                    window.location.href = "/my/banks?tab=others";
                })
            }
        })

    $("#agree_terms").click(function () {
        if ($(this).is(":checked")) {
            $('#add_bank').prop('disabled', false);
        } else {
            $('#add_bank').prop('disabled', true);
        }
    });
    /* Add bank modal ends */
    // create support ticket start
    const subject = document.getElementById('subject');
    if(subject){
        subject.addEventListener('change', onChangesubject);
    }
    function onChangesubject(e) {
      if(e.target.value == ''){
        $("#error_subject").html("Please enter valid subject.").show();
      }else{
        $("#error_subject").html("").hide();
      }
    }
    const description = document.getElementById('description');
    if(description){
        description.addEventListener('change', onChangedescription);
    }
    function onChangedescription(e) {
      if(e.target.value == ''){
        $("#error_ticket_description").html("Please enter description.").show();
      }else{
        $("#error_ticket_description").html("").hide();
      }
    }
    $('#ticket_type_id').on('change', function(e) {
        if (e.target.value == 0){
            $("#error_ticket_type").html("Please select ticket type.").show();
        }else{
            $("#error_ticket_type").html("").hide();
        }
    });
    $("#supportTicket").submit(function(event) {
        let name = document.forms["supportTicketForm"]["name"].value;
        let description = document.forms["supportTicketForm"]["description"].value;

        var validsupportTicketForm = true;
        if(name == ''){
            $("#error_subject").html("Please enter valid subject.").show();
            validsupportTicketForm = false;
        }else{
            $("#error_subject").html("").hide();
        }

        if(description == ''){
            $("#error_ticket_description").html("Please enter description.").show();
            validsupportTicketForm = false;
        }else{
            $("#error_ticket_description").html("").hide();
        }

        if ($("#ticket_type_id").val() == 0){
            $("#error_ticket_type").html("Please select ticket type.").show();
            validsupportTicketForm = false;
        }else{
            $("#error_ticket_type").html("").hide();
        }

        if(!validsupportTicketForm){
           return false;
        }else{
            swal("Success!", "Ticket successfully created!", "success");
        }
    });
    // create support ticket form ends
    $("#dropdown-all-header").click(function(){
        $("#search-bar-dropdwon-header").slideToggle();
    });
    $("#dropdown-all-header-mobile").click(function(){
        $("#search-bar-dropdwon-header-mobile").slideToggle();
    });
    // catalogue js start
    $('.build-catlog, .mobile-menu-strip').click(function(){
        $('.catalouge-main').show();
        $('.cat-menu-inner').hide();
    })
    $('.cat-close-mark').click(function(){
        $('.catalouge-main').hide();
    })
    $(".cat-menu-main-row").click(function(){
        $('.cat-menu-main').hide();
        //$('.cat-menu-inner').show();
        $(this).parent().next().show();
    })
    $(".back-to-menu-box").click(function(){
        $('.cat-menu-main').show();
        $('.cat-menu-inner').hide();
    })
    // catalogue js end
//    $(".build-header, .footer-dark, .cat-header, .mobile-header").on("click",function() {
//        if ($(".build-header, .footer-dark, .cat-header").hasClass('bg-1')) {
//            $(".build-header, .footer-dark, .cat-header").removeClass('bg-1').addClass('bg-2');
//        } else if ($(".build-header, .footer-dark, .cat-header").hasClass('bg-2')) {
//            $(".build-header, .footer-dark, .cat-header").removeClass('bg-2').addClass('bg-3');
//        } else if ($(".build-header, .footer-dark, .cat-header").hasClass('bg-3')) {
//            $(".build-header, .footer-dark, .cat-header").removeClass('bg-3').addClass('bg-1');
//        }
//        if ($(".bg-change-2").hasClass('bg-1')) {
//            $(".bg-change-2").removeClass('bg-1').addClass('bg-2');
//        } else if ($(".bg-change-2").hasClass('bg-2')) {
//            $(".bg-change-2").removeClass('bg-2').addClass('bg-3');
//        } else if ($(".bg-change-2").hasClass('bg-3')) {
//            $(".bg-change-2").removeClass('bg-3').addClass('bg-1');
//        }
//    });
    $(".bg-change").on("click",function() {
        if ($(".bg-change-2").hasClass('bg-1')) {
            $(".bg-change-2").removeClass('bg-1').addClass('bg-2');
        } else if ($(".bg-change-2").hasClass('bg-2')) {
            $(".bg-change-2").removeClass('bg-2').addClass('bg-3');
        } else if ($(".bg-change-2").hasClass('bg-3')) {
            $(".bg-change-2").removeClass('bg-3').addClass('bg-1');
        }
        if ($(".build-header, .footer-dark, .cat-header").hasClass('bg-1')) {
            $(".build-header, .footer-dark, .cat-header").removeClass('bg-1').addClass('bg-2');
        } else if ($(".build-header, .footer-dark, .cat-header").hasClass('bg-2')) {
            $(".build-header, .footer-dark, .cat-header").removeClass('bg-2').addClass('bg-3');
        } else if ($(".build-header, .footer-dark, .cat-header").hasClass('bg-3')) {
            $(".build-header, .footer-dark, .cat-header").removeClass('bg-3').addClass('bg-1');
        }
    });
    $('.catalouge-main').click(function(evt){
           if($(evt.target).closest('.catalouge-menu').length){
           }else{
                $('.catalouge-main').hide();
           }
    });
    // voice upload js start
        //webkitURL is deprecated but nevertheless
    URL = window.URL || window.webkitURL;

    var gumStream; 						//stream from getUserMedia()
    var rec; 							//Recorder.js object
    var input; 							//MediaStreamAudioSourceNode we'll be recording

    // shim for AudioContext when it's not avb.
    var AudioContext = window.AudioContext || window.webkitAudioContext;
    var audioContext //audio context to help us record


    var recordButton = document.getElementById("recordButton");
    var stopButton = document.getElementById("stopButton");
    var pauseButton = document.getElementById("pauseButton");

    if(recordButton != null){
        //add events to those 2 buttons
        recordButton.addEventListener("click", startRecording);
        stopButton.addEventListener("click", stopRecording);
        pauseButton.addEventListener("click", pauseRecording);
        document.getElementById("wave").style.display = "none";
    }

    function startRecording() {
        document.getElementById("wave").style.display = "block";
        /*
            Simple constraints object, for more advanced audio features see
            https://addpipe.com/blog/audio-constraints-getusermedia/
        */

        var constraints = { audio: true, video:false }

        /*
            Disable the record button until we get a success or fail from getUserMedia()
        */

        recordButton.disabled = true;
        stopButton.disabled = false;
        pauseButton.disabled = false

        /*
            We're using the standard promise based getUserMedia()
            https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia
        */

        navigator.mediaDevices.getUserMedia(constraints).then(function(stream) {

            /*
                create an audio context after getUserMedia is called
                sampleRate might change after getUserMedia is called, like it does on macOS when recording through AirPods
                the sampleRate defaults to the one set in your OS for your playback device

            */
            audioContext = new AudioContext();

            //update the format
            // document.getElementById("formats").innerHTML="Format: 1 channel pcm @ "+audioContext.sampleRate/1000+"kHz"

            /*  assign to gumStream for later use  */
            gumStream = stream;

            /* use the stream */
            input = audioContext.createMediaStreamSource(stream);

            /*
                Create the Recorder object and configure to record mono sound (1 channel)
                Recording 2 channels  will double the file size
            */
            rec = new Recorder(input,{numChannels:1})

            //start the recording process
            rec.record()


        }).catch(function(err) {
            //enable the record button if getUserMedia() fails
            recordButton.disabled = false;
            stopButton.disabled = true;
            pauseButton.disabled = true
        });
    }

    function pauseRecording(){

        if (rec.recording){
            //pause
            rec.stop();
            pauseButton.innerHTML="Resume";
            document.getElementById("wave").style.display = "none";
        }else{
            //resume
            rec.record()
            pauseButton.innerHTML="Pause";
            document.getElementById("wave").style.display = "block";

        }
    }

    function stopRecording() {
        document.getElementById("wave").style.display = "none";
        //disable the stop button, enable the record too allow for new recordings
        stopButton.disabled = true;
        recordButton.disabled = false;
        pauseButton.disabled = true;

        //reset button just in case the recording is stopped while paused
        pauseButton.innerHTML="Pause";

        //tell the recorder to stop the recording
        rec.stop();

        //stop microphone access
        gumStream.getAudioTracks()[0].stop();

        //create the wav blob and pass it on to createDownloadLink
        rec.exportWAV(createDownloadLink);
    }
    var voiceUploadObj = {};
    function createDownloadLink(blob) {

        var dvPreview = $("#voiceEnqPreview");

        var divCreate = $("<div class='upl-body-sec'>");
        var divCreate2 = $("<div class='pull-left left-cont-upl'>");
        var divCreate3 = $("<div class='pull-right right-cont-upl'>");
        var divCreate4 = $("<div style='clear:both;'>");

        var url = URL.createObjectURL(blob);
        var au = document.createElement('audio');
        var filename = new Date().toISOString();

        au.controls = true;
        au.src = url;

        divCreate2.append(au);

        var deleteImg = $("<img />");
        deleteImg.attr("src", '/buildmart/static/src/images/delete.png');
        deleteImg.attr("class", 'removeVoiceAttachMent');
        deleteImg.attr("id", filename+'del');
        divCreate3.append(deleteImg);

        divCreate.append(divCreate2);
        divCreate.append(divCreate3);
        divCreate.append(divCreate4);

        dvPreview.append(divCreate);

        voiceUploadObj[filename] = url;
        const isEmpty = Object.keys(voiceUploadObj).length === 0;
        if(isEmpty){
            $("#noVoice").show();
        }else{
            $("#noVoice").hide();
        }
        $('#voiceUpload').modal('toggle');
    }
    // voice upload js ends
    $(document).on('click', '.removeVoiceAttachMent', function(){
        $(this).closest('.upl-body-sec').remove();
        var ID = $(this).attr("id");
        var substringKey = ID.slice(0, -3);
        delete voiceUploadObj[substringKey];
        const isEmpty = Object.keys(voiceUploadObj).length === 0;
        if(isEmpty){
            $("#noVoice").show();
        }else{
            $("#noVoice").hide();
        }
    });

    $(".open-filter-mobile").click(function(){
        $(".mobile-filter-open").show();
        $(this).hide();
        $(".close-mark-filter").show();
    });
    $(".close-mark-filter").click(function(){
        $(".mobile-filter-open").hide();
        $(this).hide();
        $(".open-filter-mobile").show();
    });
    $('.fa-open-search-filter').click(function(){
        $(this).hide();
        $(".order-name").hide();
        $(".fa-search-filter").show();
    });
    $(".invoice-close").click(function(){
        $('.fa-open-search-filter').show();
        $(".order-name").show();
        $(".fa-search-filter").hide();
    });
    $(".order-select-dp").change(function() {
        var selectedText = $('option:selected', this).text();
        if(selectedText === "Price Quotations"){
            $('#quotations').css({"display": "block", "opacity": "1"});
            $('#accepteds').css({"display": "none", "opacity": "0"});
            $('#open-orders').css({"display": "none", "opacity": "0"});
            $('#cancelled-orders').css({"display": "none", "opacity": "0"});
            $('#rejected-orders').css({"display": "none", "opacity": "0"});
        }else if(selectedText === "Accepted Orders"){
            $('#quotations').css({"display": "none", "opacity": "0"});
            $('#accepteds').css({"display": "block", "opacity": "1"});
            $('#open-orders').css({"display": "none", "opacity": "0"});
            $('#cancelled-orders').css({"display": "none", "opacity": "0"});
            $('#rejected-orders').css({"display": "none", "opacity": "0"});
        }else if(selectedText === "Confirmed Orders"){
            $('#quotations').css({"display": "none", "opacity": "0"});
            $('#accepteds').css({"display": "none", "opacity": "0"});
            $('#open-orders').css({"display": "block", "opacity": "1"});
            $('#cancelled-orders').css({"display": "none", "opacity": "0"});
            $('#rejected-orders').css({"display": "none", "opacity": "0"});
        }else if(selectedText === "Cancelled Orders"){
            $('#quotations').css({"display": "none", "opacity": "0"});
            $('#accepteds').css({"display": "none", "opacity": "0"});
            $('#open-orders').css({"display": "none", "opacity": "0"});
            $('#cancelled-orders').css({"display": "block", "opacity": "1"});
            $('#rejected-orders').css({"display": "none", "opacity": "0"});
        }else if(selectedText === "Rejected Orders"){
            $('#quotations').css({"display": "none", "opacity": "0"});
            $('#accepteds').css({"display": "none", "opacity": "0"});
            $('#open-orders').css({"display": "none", "opacity": "0"});
            $('#cancelled-orders').css({"display": "none", "opacity": "0"});
            $('#rejected-orders').css({"display": "block", "opacity": "1"});
        }
    });
    $(".fa-down").hide();
    $( "#accordionEx .card-active:first-child" ).addClass( "active");
//    $(".card-active").click(function () {
//        $(".card-active").removeClass("active");
//        $(this).addClass("active");
//    });

});
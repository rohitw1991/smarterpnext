frappe.provide("erpnext");

frappe.provide("erpnext.stock");
frappe.require("assets/erpnext/js/controllers/stock_controller.js");

erpnext.stock.CustomItem = erpnext.stock.StockController.extend({

   items_image: function(doc) {
      var image_data;
      var dialog = new frappe.ui.Dialog({
        title:__('Images'),
        fields: [{fieldtype:'HTML', fieldname:'image_name', label:__('Images'), reqd:false,
                  description: __("")}
                ]})

        var fd = dialog.fields_dict;
        return frappe.call({
            type: "GET",
            method: "erpnext.stock.stock_custom_methods.get_details",
            args: {
              "item_name": doc.name
            },
            callback: function(r) {
              var me = this;
              if(r.message)
              {
              result_set=r.message
              this.table = $('<div id="banner-slide" style="height:200px; width:300px;  textAlign:center">\
              <ul class="bjqs">\
              </ul></div>').appendTo($(fd.image_name.wrapper));
              $.each(result_set,function(i,d) {  
              var row = $("<li>").appendTo(me.table.find("ul"));
                        $("<li>").html('<li><img src="'+d[0]+'" width="500px" text-align="center" title="secound caption"></li>')
                               .appendTo(me.table.find(row));
                  });
                  this.table.bjqs({
                  height      : 500,
                  width       : 500,
                  responsive  : true,
                  randomstart   : true
                  });
                  dialog.show();
                }
                else
                {
                  msgprint("No Images Found");
                }
              }
          });
    },
    assign_trials : function(doc, cdt, cdn){
       var d = locals[cdt][cdn]
        if (parseInt(d.trials)==1){
            this.init_trials(d)
            this.render_data(d)
            this.add_trial(d)
            this.save_data(d)
            this.remove_row()
            refresh_field('branch_dict')
        }
        else{
              alert("Click on Check Split Qty")
        }
    },
    init_trials : function(data){
      this.dialog = new frappe.ui.Dialog({
      title:__(' Styles'),
      fields: [
      {fieldtype:'Int', fieldname:'trial', label:__('Trial No'), reqd:false,
          description: __("")},
          {fieldtype:'Button', fieldname:'add_warehouse', label:__('Add'), reqd:false,
          description: __("")},
        {fieldtype:'HTML', fieldname:'styles_name', label:__('Styles'), reqd:false,
          description: __("")},
          {fieldtype:'Button', fieldname:'create_new', label:__('Ok') }
        ]
      })
      this.control_trials = this.dialog.fields_dict;
      this.div = $('<div id="myGrid" style="width:100%;height:200px;margin:10px;overflow-y:scroll"><table class="table table-bordered" style="background-color: #f9f9f9;height:10px" id="mytable">\
                <thead><tr ><td>Process</td><td>Trial No</td><td>Quality</td><td>Actual Fabric</td>\
                <td>Amendent</td><td>Remove</td></tr></thead><tbody></tbody></table></div>').appendTo($(this.control_trials.styles_name.wrapper))

      this.dialog.show();
      },
      render_data: function(data){
         var me =this;
         var $trial_data;
         if (data.branch_dict){
            $trial_data = JSON.parse(data.branch_dict)
            for(j in $trial_data)
            {
                if($trial_data[j]['trial']){
                  me.table = $(me.div).find('#mytable tbody').append('<tr><td>'+$trial_data[j]['process']+'</td><td>'+$trial_data[j]['trial']+'</td><td><input id="quality_check" class="quality_check" type="checkbox" name="quality_check" '+$trial_data[j]['quality_check']+'></td><td><input id="actual_fabric" class="quality_check" type="checkbox" name="actual_fabric" '+$trial_data[j]['actual_fabric']+'></td><td><input id="amended" class="quality_check" type="checkbox" name="amended" '+$trial_data[j]['amended']+'></td><td>&nbsp;<button  class="remove">X</button></td></tr>')  
                }
            }
         }
      },
      add_trial: function(data){
        var me = this;
        this.table;
        $(this.control_trials.add_warehouse.input).click(function(){
            this.table = $(me.div).find('#mytable tbody').append('<tr><td>'+data.process_name+'</td><td>'+me.control_trials.trial.last_value+'</td><td><input class="quality_check" type="checkbox" name="quality_check" ></td><td><input class="quality_check" type="checkbox" name="actual_fabric" ></td><td><input class="quality_check" type="checkbox" name="amended" ></td><td>&nbsp;<button  class="remove">X</button></td></tr>')
            me.remove_row()
        })
      },
      save_data : function(data){
        var me = this;
        var trials_dict={};
        var status=true;
        $(this.control_trials.create_new.input).click(function(){
            $(me.div).find("#mytable tbody tr").each(function(i) {
              var key =['process','trial', 'quality_check','actual_fabric','amended','cancel']
              var $data= {};
              trial_no = i;
              cells = $(this).find('td')
              $(cells).each(function(i) {
                 if(i==1 && parseInt($(this).text())!=(trial_no + 1)){
                    data.branch_dict ="";
                    status =false;
                    return false
                }
                var d1 = $(this).find('.quality_check').is(':checked') ? 'checked' : $(this).text();
                $data[key[i]]=d1
              })
              trials_dict[i]=($data)
        })
        if(trials_dict){
          data.branch_dict = JSON.stringify(trials_dict)
        }
        if(status==true){
          me.dialog.hide()  
        }else{
          alert("Trials must be in sequence")
        }
        
      })
    },
    remove_row : function(){
      var me =this;
      $(this.div).find('.remove').click(function(){
              $(this).parent().parent().remove()
        })
    },
    add_branch : function(doc, cdt, cdn){
      var d =locals[cdt][cdn]
      status = this.check_duplicate(d)
      if (status=='true' && d.warehouse){
        if(d.branch_list){
          d.branch_list += '\n'+d.warehouse   
        }
        else{
          d.branch_list=d.warehouse
        }
      }
      else{
        alert("process already available or process not selected")
      }
      refresh_field('process_item')
    },
    check_duplicate: function(data){
      if(data.branch_list){
        branches = (data.branch_list).split('\n')
        for(i=0;i<branches.length;i++){
          if(data.warehouse == branches[i]){
            return 'false'      
          }
        }
      }
      return 'true'
    }
  })
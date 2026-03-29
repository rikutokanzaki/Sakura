local dict = ngx.shared.sakura_switch

if not ngx.var.dispatcher_mode or ngx.var.dispatcher_mode == "" then
  ngx.var.dispatcher_mode = (dict and dict:get("mode")) or "dynamic"
end

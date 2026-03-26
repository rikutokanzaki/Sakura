local dict = ngx.shared.sakura_switch

if not ngx.var.spring_mode or ngx.var.spring_mode == "" then
  ngx.var.spring_mode = (dict and dict:get("mode")) or "sakura"
end

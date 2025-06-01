local httpc = require("resty.http").new()

local uri = (ngx.var.request_uri or ""):lower()
local ua  = (ngx.var.http_user_agent or ""):lower()

local http_patterns = {
  "union", "select", "or 1=1", "wp_login%.php",
  "%.%.%/", "/etc/passwd", "cmd%.exe",
  "sqlmap", "curl", "python", "masscan", "nmap"
}

for _, p in ipairs(http_patterns) do
  if uri:find(p, 1, true) or ua:find(p, 1, true) then
    local launcher_port = "5000"
    local launcher_address = "http://launcher:" .. launcher_port .. "/trigger/h0neytr4p"
    local res, err = httpc:request_uri(launcher_address, {
      method = "POST",
    })

    if not res then
      ngx.log(ngx.ERR, "failed to trigger: ", err)
    end

    return ngx.exec("@h0neytr4p")
  end
end

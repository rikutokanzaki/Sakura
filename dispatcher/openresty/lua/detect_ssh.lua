local http = require("resty.http")
local httpc = http.new()

local launcher_port = "5000"
local launcher_address = "http://launcher:" .. launcher_port .. "/trigger/cowrie"

local res, err = httpc:request_uri(launcher_address, {
  method = "POST",
})

if not res then
  ngx.log(ngx.ERR, "SSH honeypot tigger failed:", err)
end
local http = require("resty.http")
local httpc = http.new()

local host_ip = os.getenv("HOST_IP")
local launcher_port = "5001"
local launcher_address = "http://" .. host_ip .. ":" .. launcher_port .. "/trigger/ssh"

local res, err = httpc:request_uri(launcher_address, {
  method = "POST",
})

if not res then
  ngx.log(ngx.ERR, "SSH honeypot tigger failed:", err)
end
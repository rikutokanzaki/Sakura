local http = require("resty.http")

local upstreams = {
  wordpot   = "wordpot:80",
  h0neytr4p = "h0neytr4p:80",
}

local function split_hostport(hp)
  local h, p = string.match(hp, "^([^:]+):(%d+)$")
  return h or hp, tonumber(p) or 80
end

local function wait_upstream_ready(target, total_ms, interval_ms)
  local hp = upstreams[target]
  if not hp then return false end
  local host, port = split_hostport(hp)

  total_ms = total_ms or 4000
  interval_ms = interval_ms or 100

  local deadline = ngx.now() + (total_ms / 1000)
  while ngx.now() < deadline do
    local sock = ngx.socket.tcp()
    sock:settimeout(interval_ms)
    local ok = sock:connect(host, port)
    if ok then
      sock:close()
      return true
    end
    ngx.sleep(interval_ms / 1000)
  end
  return false
end

local raw_uri = ngx.var.request_uri or ""
local uri     = raw_uri:lower()
local dec_uri = ngx.unescape_uri(uri)
local ua      = (ngx.var.http_user_agent or ""):lower()

local high_patterns = {
  "sqlmap", "python-requests", "python", "curl", "wget", "nmap", "masscan", "nikto",
  "../", "/etc/passwd", "c:\\windows\\system32", "/proc/self/environ",
  "or 1=1", "' or '1'='1", "\" or \"1\"=\"1", "union select", "sleep(", "benchmark(",
  "cmd.exe", "powershell"
}

local wordpress_patterns = {
  "wp-login.php", "xmlrpc.php", "wp-admin",
  "wp-content", "wp-includes", "wp-json", "wp-config.php",
  "wp-comments-post.php", "wp-cron.php", "wp-"
}

local function match_any_in(strs, patterns)
  for _, s in ipairs(strs) do
    if s then
      for _, p in ipairs(patterns) do
        if s:find(p, 1, true) then
          return true
        end
      end
    end
  end
  return false
end

local is_wp   = match_any_in({ uri, dec_uri }, wordpress_patterns)
local is_high = match_any_in({ uri, dec_uri, ua }, high_patterns)

local rules = {
  { target = "wordpot",  match = function() return is_wp end },
  { target = "h0neytr4p", match = function() return (not is_wp) and is_high end },
}

local function trigger_and_proxy(target)
  local launcher_port = "5000"
  local launcher_address = "http://launcher:" .. launcher_port .. "/trigger/" .. target

  local client = http.new()
  client:set_timeout(1000)
  local _, err = client:request_uri(launcher_address, { method = "POST" })

  if err then
    ngx.log(ngx.ERR, "failed to trigger: ", err)
  end

  local ready = wait_upstream_ready(target, 4000, 100)
  if not ready then
    ngx.log(ngx.WARN, "upstream not ready for ", target, " -> fallback to heralding")
    return ngx.exec("@heralding")
  end

  return ngx.exec("@" .. target)
end

for _, rule in ipairs(rules) do
  local ok = false
  local ok_call, res = pcall(rule.match)

  if ok_call and res then
    return trigger_and_proxy(rule.target)
  end
end

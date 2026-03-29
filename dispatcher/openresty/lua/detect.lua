local http = require("resty.http")

local function current_mode()
  local dict = ngx.shared.sakura_switch
  return (dict and dict:get("mode")) or "dynamic"
end

local function standalone_http_target()
  local target = (os.getenv("DISPATCHER_HTTP_TARGET") or "h0neytr4p"):lower()
  if target == "heralding" or target == "h0neytr4p" then
    return target
  end
  return "h0neytr4p"
end

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

local function proxy(target)
  local mode = current_mode()
  ngx.var.dispatcher_mode    = mode

  return ngx.exec("@" .. target)
end

local function http_post(url)
  local client = http.new()
  client:set_timeout(1500)
  local res, err = client:request_uri(url, { method = "POST" })

  if err then
    return nil, err
  end

  if not res or res.status >= 400 then
    return nil, "bad status: " .. (res and res.status or "nil")
  end
  return res, nil
end

local function with_boot_lock(target, ttl, fn)
  local dict = ngx.shared.sakura_switch
  local key = "bootlock:" .. target

  if dict and dict:add(key, true, ttl or 5) then
    local ok, err = pcall(fn)

    if not ok then
      ngx.log(ngx.ERR, "boot lock fn error: ", err)
    end

    if dict then dict:delete(key) end
  end
end

local upstreams = {
  wordpot   = { name = "wordpot",   port = 80 },
  h0neytr4p = { name = "h0neytr4p", port = 80 },
}

local function wait_upstream_ready(target, total_ms, interval_ms)
  local hp = upstreams[target]
  if not hp then return false end

  local host = hp.host or hp.name
  local port = tonumber(hp.port)

  total_ms = total_ms or 15000
  interval_ms = interval_ms or 200

  ngx.log(ngx.INFO, "[wait] target=", target, " host=", host, " port=", port, " total_ms=", total_ms)
  local deadline = ngx.now() + (total_ms / 1000)
  while ngx.now() < deadline do
    local sock = ngx.socket.tcp()
    sock:settimeout(interval_ms)
    local ok = sock:connect(host, port)
    if ok then
      sock:close()
      ngx.log(ngx.INFO, "[wait] target=", target, " is ready")
      return true
    end
    ngx.sleep(interval_ms / 1000)
  end

  ngx.log(ngx.WARN, "[wait] timeout waiting for target=", target)
  return false
end

local function trigger_and_proxy(target)
  local launcher_port = "5000"
  local launcher_address = "http://launcher:" .. launcher_port .. "/trigger/" .. target
  ngx.log(ngx.INFO, "[trigger+proxy] ", target)

  local mode = current_mode()
  ngx.var.dispatcher_mode    = mode

  with_boot_lock("trg:" .. target, 5, function()
    local client = http.new()
    client:set_timeout(1000)
    local res, err = client:request_uri(launcher_address, { method = "POST" })

    if err then
      ngx.log(ngx.ERR, "[trigger+proxy] error: ", err)
    else
      ngx.log(ngx.INFO, "[trigger+proxy] status=", res and res.status)
    end
  end)

  local ready = wait_upstream_ready(target, 15000, 200)
  if not ready then
    ngx.log(ngx.WARN, "[trigger+proxy] upstream not ready for ", target, " -> fallback to heralding")
    return ngx.exec("@heralding")
  end

  return ngx.exec("@" .. target)
end

local high_patterns = {
  "sqlmap", "python-requests", "python", "curl", "wget", "nmap", "masscan", "nikto", "phpunit",
  "../", "/etc/passwd", "c:\\windows\\system32", ".env", "/proc/self/environ",
  "or 1=1", "' or '1'='1", "\" or \"1\"=\"1", "union select", "sleep(", "benchmark(",
  "cmd.exe", "powershell"
}

local wordpress_patterns = {
  "wp-login.php", "xmlrpc.php", "wp-admin",
  "wp-content", "wp-includes", "wp-json", "wp-config.php",
  "wp-comments-post.php", "wp-cron.php", "wp-"
}

for i, v in ipairs(high_patterns) do
  high_patterns[i] = v:lower()
end

for i, v in ipairs(wordpress_patterns) do
  wordpress_patterns[i] = v:lower()
end

local raw_uri = ngx.var.request_uri or ""
local uri     = raw_uri:lower()
local dec_uri = ngx.unescape_uri(uri)
local ua      = (ngx.var.http_user_agent or ""):lower()

local is_wp   = match_any_in({ uri, dec_uri }, wordpress_patterns)
local is_high = match_any_in({ uri, dec_uri, ua }, high_patterns)

local target
if is_wp then
  target = "wordpot"
elseif (not is_wp) and is_high then
  target = "h0neytr4p"
else
  target = "heralding"
end

local mode = current_mode()

if mode == "dynamic" then
  if target == "wordpot" or target == "h0neytr4p" then
    return trigger_and_proxy(target)
  else
    return proxy("heralding")
  end
end

if mode == "static" then
  return proxy(target)
end

if mode == "standalone" then
  return proxy(standalone_http_target())
end

return proxy("heralding")

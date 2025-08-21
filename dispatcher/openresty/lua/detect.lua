local httpc = require("resty.http").new()

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

  local res, err = httpc:request_uri(launcher_address, {
    method = "POST"
  })

  if not res then
    ngx.log(ngx.ERR, "failed to trigger: ", err)
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

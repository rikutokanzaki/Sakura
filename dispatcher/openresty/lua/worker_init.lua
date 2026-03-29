local dict = ngx.shared.sakura_switch
local http = require("resty.http")

local function normalize_mode(mode)
  if not mode then
    return "dynamic"
  end

  local lower = string.lower(mode)

  if lower == "dynamic" or lower == "static" or lower == "standalone" or lower == "rotate" then
    return lower
  end

  return "dynamic"
end

local function read_rotate_interval()
  local value = tonumber(os.getenv("ROTATE_INTERVAL") or "1020")
  if value and value > 0 then
    return value
  end
  return 1020
end

local function resolve_mode(configured_mode, rotate_interval)
  if configured_mode ~= "rotate" then
    return configured_mode
  end

  local modes = { "dynamic", "static", "standalone" }
  local slot = math.floor(ngx.time() / rotate_interval) % #modes + 1
  return modes[slot]
end

local function sync_mode(configured_mode, rotate_interval)
  local new_mode = resolve_mode(configured_mode, rotate_interval)
  local old_mode = dict:get("mode")
  if old_mode ~= new_mode then
    dict:set("mode", new_mode)
    ngx.log(ngx.INFO, "[mode-rotate] ", old_mode, " -> ", new_mode)
    return new_mode
  end
  return nil
end

local function apply_mode(mode)
  local c = http.new()
  c:set_timeout(1500)
  local res, err = c:request_uri("http://launcher:5000/apply-mode/" .. mode, {
    method = "POST"
  })

  if err then
    ngx.log(ngx.ERR, "[mode-apply] failed: ", err)
    return
  end

  if not res or res.status >= 400 then
    ngx.log(ngx.WARN, "[mode-apply] bad status: ", res and res.status or "nil")
  end
end

local configured_mode = normalize_mode(os.getenv("DISPATCHER_MODE"))
local selected_profile = (os.getenv("SELECTED_PROFILE") or "standard"):lower()
local rotate_interval = read_rotate_interval()
local initial_mode = resolve_mode(configured_mode, rotate_interval)

dict:set("mode", initial_mode)
ngx.log(ngx.INFO, "[mode-init] mode=", initial_mode, " (configured=", configured_mode, ")")

if configured_mode ~= "rotate" then
  return
end

if selected_profile == "http" then
  apply_mode(initial_mode)
end

local ok, err = ngx.timer.every(1, function()
  local ok_inner, changed_mode_or_err = pcall(sync_mode, configured_mode, rotate_interval)
  if not ok_inner then
    ngx.log(ngx.ERR, "sync timer callback error: ", changed_mode_or_err)
    return
  end

  if selected_profile == "http" and changed_mode_or_err then
    apply_mode(changed_mode_or_err)
  end
end
if not ok then ngx.log(ngx.ERR, "sync timer error: ", err) end

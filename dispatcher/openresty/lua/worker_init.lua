local http = require("resty.http")
local dict = ngx.shared.sakura_switch

local function normalize_mode(mode)
  if not mode then
    return "dynamic"
  end

  local lower = string.lower(mode)
  if lower == "sakura" then
    return "dynamic"
  end
  if lower == "yozakura" then
    return "static"
  end
  if lower == "tsubomi" then
    return "standalone"
  end
  if lower == "spring" then
    return "rotate"
  end

  if lower == "dynamic" or lower == "static" or lower == "standalone" or lower == "rotate" then
    return lower
  end

  return "dynamic"
end

local function fetch_current_mode()
  local c = http.new()
  c:set_timeout(2000)

  local res, err = c:request_uri("http://launcher:5000/current-mode", {
    method = "GET"
  })

  if err then
    ngx.log(ngx.ERR, "[mode-fetch] failed: ", err)
    return nil
  end

  if res.status == 200 then
    local mode = normalize_mode(res.body)
    return mode
  end

  return nil
end

local function sync_mode()
  local new_mode = fetch_current_mode()
  if new_mode then
    local old_mode = dict:get("mode")
    if old_mode ~= new_mode then
      dict:set("mode", new_mode)
      ngx.log(ngx.INFO, "[mode-sync] ", old_mode, " -> ", new_mode)
    end
  end
end

local configured_mode = normalize_mode(os.getenv("DISPATCHER_MODE"))
dict:set("mode", configured_mode)
ngx.log(ngx.INFO, "[mode-init] mode=", configured_mode, " (configured)")

if configured_mode ~= "rotate" then
  return
end

local ok, err = ngx.timer.at(0, function()
  local initial_mode = fetch_current_mode()
  if initial_mode then
    dict:set("mode", initial_mode)
    ngx.log(ngx.INFO, "[mode-init] mode=", initial_mode)
  end
end)
if not ok then ngx.log(ngx.ERR, "init timer error: ", err) end

local ok, err = ngx.timer.every(10, sync_mode)
if not ok then ngx.log(ngx.ERR, "sync timer error: ", err) end

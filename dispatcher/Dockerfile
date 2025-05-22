FROM openresty/openresty:1.21.4.1-0-jammy

RUN /usr/local/openresty/luajit/bin/luarocks install lua-resty-http 

COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/
COPY lua/detect_http.lua /usr/local/openresty/nginx/lua/detect_http.lua
COPY lua/detect_ssh.lua /usr/local/openresty/nginx/lua/detect_ssh.lua

CMD ["openresty", "-g", "daemon off;"]
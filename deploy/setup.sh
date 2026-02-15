#!/bin/bash
# ecom_agent 部署脚本 - 适用于 Ubuntu/Debian
# 用法: sudo bash setup.sh [SERVER_IP]
# 示例: sudo bash setup.sh 192.168.3.100
#
# 前提条件：
#   1. Redis 已安装并运行
#   2. 项目代码已拷贝到 /opt/ecom_agent/
#   3. 前端已构建（frontend/dist 目录存在）

set -e
trap 'echo ""; echo "ERROR: 部署在上面的步骤失败，请检查错误信息后重新运行。"; exit 1' ERR

APP_DIR="/opt/ecom_agent"
BACKEND_DIR="$APP_DIR/backend"
FRONTEND_DIR="$APP_DIR/frontend"
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="ecom-agent"
NGINX_CONF="ecom-agent"
SERVER_IP="${1:-192.168.3.100}"

echo "===== ecom_agent 部署 ====="
echo "  目标 IP: ${SERVER_IP}"
echo ""

# ---------- 前置检查 ----------
if [ ! -d "$APP_DIR" ]; then
    echo "ERROR: $APP_DIR 不存在，请先拷贝项目文件。"
    exit 1
fi
if [ ! -d "$FRONTEND_DIR/dist" ]; then
    echo "ERROR: 前端未构建，请先在开发机执行 npm run build。"
    exit 1
fi
if ! systemctl is-active --quiet redis-server 2>/dev/null; then
    echo "WARNING: Redis 未运行，将使用文件派发作为降级方案。"
fi

# ---------- 1. 系统依赖 ----------
echo "[1/7] 安装系统依赖..."
apt-get update -qq
apt-get install -y python3 python3-venv python3-pip nginx

# ---------- 2. 创建用户 ----------
echo "[2/7] 创建 ecom 用户..."
if ! id "ecom" &>/dev/null; then
    useradd -r -s /bin/false -d "$APP_DIR" ecom
fi

# ---------- 3. Python 虚拟环境 ----------
echo "[3/7] 创建 Python 虚拟环境并安装依赖..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt" -q

# ---------- 4. 后端 .env ----------
echo "[4/7] 配置后端环境变量..."
if [ ! -f "$BACKEND_DIR/.env" ]; then
    cat > "$BACKEND_DIR/.env" << EOF
# 注意：值不要加引号，systemd EnvironmentFile 会把引号当作值的一部分
CALLBACK_BASE_URL=http://${SERVER_IP}
CORS_ORIGINS=http://${SERVER_IP}
REDIS_URL=redis://localhost:6379/0
EOF
    echo "  已创建 $BACKEND_DIR/.env（请根据需要修改）"
else
    echo "  $BACKEND_DIR/.env 已存在，跳过"
fi

# 确保数据目录存在
mkdir -p "$BACKEND_DIR/data"
mkdir -p "$BACKEND_DIR/data/rpa_tasks"

# ---------- 5. Nginx ----------
echo "[5/7] 配置 Nginx..."
sed "s/192.168.3.100/${SERVER_IP}/g" "$APP_DIR/deploy/nginx.conf" \
    > /etc/nginx/sites-available/${NGINX_CONF}
ln -sf /etc/nginx/sites-available/${NGINX_CONF} /etc/nginx/sites-enabled/${NGINX_CONF}
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

# ---------- 6. 权限 ----------
echo "[6/7] 设置文件权限..."
chown -R ecom:ecom "$APP_DIR"

# ---------- 7. systemd 服务 ----------
echo "[7/7] 配置并启动后端服务..."
cp "$APP_DIR/deploy/ecom-agent.service" /etc/systemd/system/${SERVICE_NAME}.service
systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}

# 等待启动
sleep 2
if systemctl is-active --quiet ${SERVICE_NAME}; then
    echo ""
    echo "===== 部署完成 ====="
else
    echo ""
    echo "===== 服务启动失败，请检查日志 ====="
    journalctl -u ${SERVICE_NAME} --no-pager -n 20
    exit 1
fi

echo ""
echo "  后端服务: systemctl status ${SERVICE_NAME}"
echo "  后端日志: journalctl -u ${SERVICE_NAME} -f"
echo "  Nginx:    systemctl status nginx"
echo ""
echo "  访问地址: http://${SERVER_IP}"
echo "  API 地址: http://${SERVER_IP}/api/health"
echo ""
echo "如需修改配置："
echo "  编辑 $BACKEND_DIR/.env 后执行 systemctl restart ${SERVICE_NAME}"

#!/bin/bash
# 多区域并发测试启动脚本

cd /home/ubuntu/codes/nova/performance

# 区域配置
declare -A REGIONS
REGIONS=(
    ["us-east-1"]="us.amazon.nova-2-lite-v1:0"
    ["us-west-1"]="global.amazon.nova-2-lite-v1:0"
    ["eu-west-1"]="eu.amazon.nova-2-lite-v1:0"
    ["eu-central-1"]="eu.amazon.nova-2-lite-v1:0"
    ["ap-northeast-1"]="jp.amazon.nova-2-lite-v1:0"
)

echo "================================"
echo "🚀 启动多区域并发测试"
echo "================================"
echo ""

# 为每个区域启动测试
for region in "${!REGIONS[@]}"; do
    model_id="${REGIONS[$region]}"
    region_safe="${region//-/_}"

    echo "📍 区域: $region"
    echo "   模型: $model_id"

    # 创建区域专属的守护进程脚本
    daemon_script="daemon_${region_safe}.sh"
    cat > "$daemon_script" << EOF
#!/bin/bash
# $region 测试守护进程

TEST_SCRIPT="test_concurrent_96h_robust.py"
LOG_FILE="concurrent_96h_${region_safe}.log"
PID_FILE="concurrent_96h_${region_safe}.pid"
DAEMON_LOG="daemon_${region_safe}.log"

cd /home/ubuntu/codes/nova/performance

echo "🛡️  启动 $region 测试守护进程" > "\$DAEMON_LOG"
echo "================================" >> "\$DAEMON_LOG"
echo "测试脚本: \$TEST_SCRIPT" >> "\$DAEMON_LOG"
echo "日志文件: \$LOG_FILE" >> "\$DAEMON_LOG"
echo "PID文件: \$PID_FILE" >> "\$DAEMON_LOG"
echo "================================" >> "\$DAEMON_LOG"
echo "" >> "\$DAEMON_LOG"

while true; do
    if [ -f "\$PID_FILE" ]; then
        PID=\$(cat "\$PID_FILE")

        if ps -p "\$PID" > /dev/null 2>&1; then
            echo "[\$(date '+%Y-%m-%d %H:%M:%S')] ✅ 测试正常运行 (PID: \$PID)" >> "\$DAEMON_LOG"
            sleep 300  # 每5分钟检查一次
            continue
        else
            echo "[\$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  进程已停止，准备重启..." >> "\$DAEMON_LOG"
        fi
    else
        echo "[\$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  未找到PID文件，启动新进程..." >> "\$DAEMON_LOG"
    fi

    echo "[\$(date '+%Y-%m-%d %H:%M:%S')] 🚀 启动测试..." >> "\$DAEMON_LOG"
    python3 "\$TEST_SCRIPT" --region "$region" --model "$model_id" >> "\$LOG_FILE" 2>&1 &
    NEW_PID=\$!
    echo "\$NEW_PID" > "\$PID_FILE"
    echo "[\$(date '+%Y-%m-%d %H:%M:%S')] ✅ 测试已启动 (PID: \$NEW_PID)" >> "\$DAEMON_LOG"

    sleep 5
done
EOF

    chmod +x "$daemon_script"

    # 启动守护进程
    nohup bash "$daemon_script" > /dev/null 2>&1 &
    DAEMON_PID=$!
    echo "   守护进程 PID: $DAEMON_PID"

    # 等待测试进程启动
    sleep 3

    # 检查测试进程
    pid_file="concurrent_96h_${region_safe}.pid"
    if [ -f "$pid_file" ]; then
        test_pid=$(cat "$pid_file")
        if ps -p "$test_pid" > /dev/null 2>&1; then
            echo "   ✅ 测试进程启动成功 (PID: $test_pid)"
        else
            echo "   ⚠️  测试进程启动失败"
        fi
    fi

    echo ""
done

echo "================================"
echo "✅ 所有区域测试已启动"
echo "================================"
echo ""
echo "📊 查看状态:"
echo "   ps aux | grep test_concurrent_96h_robust.py"
echo ""
echo "📝 查看日志:"
echo "   tail -f daemon_*.log"
echo "   tail -f concurrent_96h_*.log"
echo ""
echo "📂 数据目录:"
for region in "${!REGIONS[@]}"; do
    region_safe="${region//-/_}"
    echo "   concurrent_96h_data_${region_safe}/"
done
echo ""

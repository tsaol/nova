#!/bin/bash
# 多区域测试状态监控

clear
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║          多区域96小时并发测试 - 实时监控                         ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# 区域列表
REGIONS=("us-west-2" "us-east-1" "us-west-1" "eu-west-2" "eu-central-1" "ap-northeast-1" "ap-southeast-1")

echo "📊 测试进程状态"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for region in "${REGIONS[@]}"; do
    region_safe="${region//-/_}"
    pid_file="concurrent_96h_${region_safe}.pid"

    if [ "$region" == "us-west-2" ]; then
        pid_file="concurrent_96h.pid"
    fi

    echo -n "📍 $region: "

    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "✅ 运行中 (PID: $pid)"
        else
            echo "❌ 已停止"
        fi
    else
        echo "⚠️  未找到PID文件"
    fi
done

echo ""
echo "📈 数据收集统计"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for region in "${REGIONS[@]}"; do
    region_safe="${region//-/_}"

    if [ "$region" == "us-west-2" ]; then
        data_dir="concurrent_96h_data"
    else
        data_dir="concurrent_96h_data_${region_safe}"
    fi

    if [ -d "$data_dir" ]; then
        csv_file=$(ls -t "$data_dir"/*.csv 2>/dev/null | head -1)
        if [ -f "$csv_file" ]; then
            lines=$(($(wc -l < "$csv_file") - 1))
            rounds=$((lines / 3))
            size=$(du -h "$csv_file" | cut -f1)

            echo "📍 $region:"
            echo "   数据记录: $lines 条 ($rounds 轮)"
            echo "   文件大小: $size"

            # 显示最新一条数据
            last_line=$(tail -1 "$csv_file")
            timestamp=$(echo "$last_line" | cut -d',' -f1)
            concurrency=$(echo "$last_line" | cut -d',' -f2)
            echo "   最新更新: $timestamp"
            echo "   当前并发: $concurrency"
            echo ""
        fi
    fi
done

echo "💾 系统资源"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "磁盘使用: $(df -h . | tail -1 | awk '{print $3 " / " $2 " (" $5 ")"}')"
echo "内存使用: $(free -h | grep Mem | awk '{print $3 " / " $2}')"
echo ""

echo "🔧 快捷命令"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "查看所有进程: ps aux | grep test_concurrent_96h_robust.py | grep -v grep"
echo "查看守护日志: tail -f daemon_*.log"
echo "查看测试日志: tail -f concurrent_96h_*.log"
echo "停止所有测试: pkill -f test_concurrent_96h_robust.py"
echo ""

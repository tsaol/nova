#!/usr/bin/env python3
"""
多区域 Nova 性能测试数据分析与可视化
"""
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np
from datetime import datetime

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")

# 区域配置
REGIONS = {
    'us-west-2': {'name': 'US West 2 (Oregon)', 'color': '#FF6B6B'},
    'us-east-1': {'name': 'US East 1 (Virginia)', 'color': '#4ECDC4'},
    'us-west-1': {'name': 'US West 1 (California)', 'color': '#45B7D1'},
    'eu-west-2': {'name': 'EU West 2 (London)', 'color': '#FFA07A'},
    'eu-central-1': {'name': 'EU Central 1 (Frankfurt)', 'color': '#98D8C8'},
    'ap-northeast-1': {'name': 'AP Northeast 1 (Tokyo)', 'color': '#F7DC6F'},
    'ap-southeast-1': {'name': 'AP Southeast 1 (Singapore)', 'color': '#BB8FCE'}
}

def load_all_data():
    """加载所有区域的数据"""
    all_data = []
    base_path = Path('/home/ubuntu/codes/nova/performance')

    for region_code in REGIONS.keys():
        if region_code == 'us-west-2':
            data_dir = base_path / 'concurrent_96h_data_us_west_2'
        else:
            region_suffix = region_code.replace('-', '_')
            data_dir = base_path / f'concurrent_96h_data_{region_suffix}'

        csv_files = list(data_dir.glob('concurrent_96h_image_*.csv'))

        if csv_files:
            for csv_file in csv_files:
                df = pd.read_csv(csv_file)
                df['region'] = region_code
                df['region_name'] = REGIONS[region_code]['name']
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                all_data.append(df)
                print(f"Loaded {len(df)} records from {region_code}")

    if not all_data:
        raise ValueError("No data files found!")

    return pd.concat(all_data, ignore_index=True)

def plot_latency_by_region_and_tier(df):
    """1. 各区域按服务层级的平均延迟对比"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Average Latency by Region and Service Tier', fontsize=16, fontweight='bold')

    tiers = ['flex', 'default', 'priority']

    for idx, tier in enumerate(tiers):
        ax = axes[idx]
        tier_data = df[df['tier'] == tier].groupby('region_name')['avg_server_latency'].mean().sort_values()

        colors = [REGIONS[region]['color'] for region in df[df['tier'] == tier].groupby('region')['avg_server_latency'].mean().sort_values().index]

        tier_data.plot(kind='barh', ax=ax, color=colors)
        ax.set_title(f'{tier.upper()} Tier', fontsize=14, fontweight='bold')
        ax.set_xlabel('Average Latency (ms)', fontsize=12)
        ax.set_ylabel('')
        ax.grid(axis='x', alpha=0.3)

        # 添加数值标签
        for i, v in enumerate(tier_data.values):
            ax.text(v + 50, i, f'{v:.0f}ms', va='center', fontsize=10)

    plt.tight_layout()
    plt.savefig('/home/ubuntu/codes/nova/performance/chart_1_latency_by_region_tier.png', dpi=300, bbox_inches='tight')
    print("✅ Chart 1 saved: chart_1_latency_by_region_tier.png")

def plot_latency_by_concurrency(df):
    """2. 不同并发级别下的延迟对比"""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Latency by Concurrency Level (All Regions)', fontsize=16, fontweight='bold')

    concurrencies = sorted(df['concurrency'].unique())
    tiers = ['flex', 'default', 'priority']

    for idx, tier in enumerate(tiers):
        ax = axes[idx]
        tier_data = df[df['tier'] == tier].groupby('concurrency')['avg_server_latency'].agg(['mean', 'std'])

        ax.bar(range(len(concurrencies)), tier_data['mean'],
               yerr=tier_data['std'], capsize=5, color='#3498db', alpha=0.7)
        ax.set_title(f'{tier.upper()} Tier', fontsize=14, fontweight='bold')
        ax.set_xlabel('Concurrency Level', fontsize=12)
        ax.set_ylabel('Average Latency (ms)', fontsize=12)
        ax.set_xticks(range(len(concurrencies)))
        ax.set_xticklabels(concurrencies)
        ax.grid(axis='y', alpha=0.3)

        # 添加数值标签
        for i, v in enumerate(tier_data['mean'].values):
            ax.text(i, v + tier_data['std'].values[i] + 50, f'{v:.0f}ms',
                   ha='center', va='bottom', fontsize=10)

    plt.tight_layout()
    plt.savefig('/home/ubuntu/codes/nova/performance/chart_2_latency_by_concurrency.png', dpi=300, bbox_inches='tight')
    print("✅ Chart 2 saved: chart_2_latency_by_concurrency.png")

def plot_latency_timeline(df):
    """3. 延迟时间序列图（按区域）"""
    fig, ax = plt.subplots(figsize=(16, 8))

    for region_code, config in REGIONS.items():
        region_data = df[(df['region'] == region_code) & (df['tier'] == 'default')]
        if len(region_data) > 0:
            # 按小时聚合数据
            region_data = region_data.set_index('timestamp').resample('1H')['avg_server_latency'].mean()
            ax.plot(region_data.index, region_data.values,
                   label=config['name'], color=config['color'], linewidth=2, alpha=0.8)

    ax.set_title('Latency Timeline (Default Tier, Hourly Average)', fontsize=16, fontweight='bold')
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Average Latency (ms)', fontsize=12)
    ax.legend(loc='best', fontsize=10)
    ax.grid(alpha=0.3)
    plt.xticks(rotation=45)

    plt.tight_layout()
    plt.savefig('/home/ubuntu/codes/nova/performance/chart_3_latency_timeline.png', dpi=300, bbox_inches='tight')
    print("✅ Chart 3 saved: chart_3_latency_timeline.png")

def plot_success_rate(df):
    """4. 各区域成功率统计"""
    fig, ax = plt.subplots(figsize=(12, 6))

    success_rate = df.groupby('region_name').apply(
        lambda x: (x['successful'].sum() / (x['successful'].sum() + x['failed'].sum())) * 100
    ).sort_values(ascending=False)

    colors = [REGIONS[region]['color'] for region in df.groupby('region').apply(
        lambda x: (x['successful'].sum() / (x['successful'].sum() + x['failed'].sum())) * 100
    ).sort_values(ascending=False).index]

    success_rate.plot(kind='bar', ax=ax, color=colors, alpha=0.8)
    ax.set_title('Success Rate by Region', fontsize=16, fontweight='bold')
    ax.set_xlabel('Region', fontsize=12)
    ax.set_ylabel('Success Rate (%)', fontsize=12)
    ax.set_ylim([98, 100.5])
    ax.axhline(y=100, color='green', linestyle='--', alpha=0.5, label='100%')
    ax.grid(axis='y', alpha=0.3)
    plt.xticks(rotation=45, ha='right')

    # 添加数值标签
    for i, v in enumerate(success_rate.values):
        ax.text(i, v + 0.1, f'{v:.2f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

    plt.tight_layout()
    plt.savefig('/home/ubuntu/codes/nova/performance/chart_4_success_rate.png', dpi=300, bbox_inches='tight')
    print("✅ Chart 4 saved: chart_4_success_rate.png")

def plot_tier_comparison_heatmap(df):
    """5. 服务层级性能热力图"""
    fig, ax = plt.subplots(figsize=(10, 8))

    # 创建数据透视表
    pivot_data = df.groupby(['region_name', 'tier'])['avg_server_latency'].mean().unstack()
    pivot_data = pivot_data[['flex', 'default', 'priority']]  # 确保顺序

    sns.heatmap(pivot_data, annot=True, fmt='.0f', cmap='RdYlGn_r',
                cbar_kws={'label': 'Latency (ms)'}, ax=ax, linewidths=0.5)
    ax.set_title('Service Tier Performance Heatmap (Average Latency)', fontsize=16, fontweight='bold')
    ax.set_xlabel('Service Tier', fontsize=12)
    ax.set_ylabel('Region', fontsize=12)

    plt.tight_layout()
    plt.savefig('/home/ubuntu/codes/nova/performance/chart_5_tier_heatmap.png', dpi=300, bbox_inches='tight')
    print("✅ Chart 5 saved: chart_5_tier_heatmap.png")

def plot_token_statistics(df):
    """6. Token 消耗统计"""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle('Token Consumption Statistics', fontsize=16, fontweight='bold')

    # 输入 tokens
    ax1 = axes[0]
    input_tokens = df.groupby('region_name')['avg_input_tokens'].mean().sort_values()
    colors = [REGIONS[region]['color'] for region in df.groupby('region')['avg_input_tokens'].mean().sort_values().index]
    input_tokens.plot(kind='barh', ax=ax1, color=colors, alpha=0.8)
    ax1.set_title('Average Input Tokens', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Tokens', fontsize=12)
    ax1.grid(axis='x', alpha=0.3)
    for i, v in enumerate(input_tokens.values):
        ax1.text(v + 10, i, f'{v:.0f}', va='center', fontsize=10)

    # 输出 tokens
    ax2 = axes[1]
    output_tokens = df.groupby('region_name')['avg_output_tokens'].mean().sort_values()
    colors = [REGIONS[region]['color'] for region in df.groupby('region')['avg_output_tokens'].mean().sort_values().index]
    output_tokens.plot(kind='barh', ax=ax2, color=colors, alpha=0.8)
    ax2.set_title('Average Output Tokens', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Tokens', fontsize=12)
    ax2.grid(axis='x', alpha=0.3)
    for i, v in enumerate(output_tokens.values):
        ax2.text(v + 2, i, f'{v:.0f}', va='center', fontsize=10)

    plt.tight_layout()
    plt.savefig('/home/ubuntu/codes/nova/performance/chart_6_token_statistics.png', dpi=300, bbox_inches='tight')
    print("✅ Chart 6 saved: chart_6_token_statistics.png")

def plot_latency_distribution(df):
    """7. 延迟分布箱线图"""
    fig, ax = plt.subplots(figsize=(14, 8))

    # 准备数据
    plot_data = []
    labels = []
    colors_list = []

    for region_code, config in REGIONS.items():
        region_data = df[(df['region'] == region_code) & (df['tier'] == 'default')]['avg_server_latency']
        if len(region_data) > 0:
            plot_data.append(region_data.values)
            labels.append(config['name'])
            colors_list.append(config['color'])

    bp = ax.boxplot(plot_data, labels=labels, patch_artist=True, showmeans=True)

    # 设置颜色
    for patch, color in zip(bp['boxes'], colors_list):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    ax.set_title('Latency Distribution by Region (Default Tier)', fontsize=16, fontweight='bold')
    ax.set_ylabel('Latency (ms)', fontsize=12)
    ax.grid(axis='y', alpha=0.3)
    plt.xticks(rotation=45, ha='right')

    plt.tight_layout()
    plt.savefig('/home/ubuntu/codes/nova/performance/chart_7_latency_distribution.png', dpi=300, bbox_inches='tight')
    print("✅ Chart 7 saved: chart_7_latency_distribution.png")

def generate_summary_report(df):
    """生成汇总报告"""
    print("\n" + "="*80)
    print("📊 MULTI-REGION PERFORMANCE TEST SUMMARY REPORT")
    print("="*80)

    print(f"\n📅 Test Period:")
    print(f"   Start: {df['timestamp'].min()}")
    print(f"   End:   {df['timestamp'].max()}")
    print(f"   Duration: {(df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600:.1f} hours")

    print(f"\n📈 Total Statistics:")
    print(f"   Total API Calls: {df['successful'].sum() + df['failed'].sum():,}")
    print(f"   Successful: {df['successful'].sum():,}")
    print(f"   Failed: {df['failed'].sum():,}")
    print(f"   Success Rate: {(df['successful'].sum() / (df['successful'].sum() + df['failed'].sum()) * 100):.3f}%")

    print(f"\n🌍 Regional Performance (Default Tier):")
    regional_stats = df[df['tier'] == 'default'].groupby('region_name').agg({
        'avg_server_latency': ['mean', 'min', 'max', 'std'],
        'successful': 'sum',
        'failed': 'sum'
    }).round(2)

    for region in regional_stats.index:
        stats = regional_stats.loc[region]
        success_rate = stats[('successful', 'sum')] / (stats[('successful', 'sum')] + stats[('failed', 'sum')]) * 100
        print(f"\n   {region}:")
        print(f"      Avg Latency: {stats[('avg_server_latency', 'mean')]:.0f}ms")
        print(f"      Min Latency: {stats[('avg_server_latency', 'min')]:.0f}ms")
        print(f"      Max Latency: {stats[('avg_server_latency', 'max')]:.0f}ms")
        print(f"      Std Dev: {stats[('avg_server_latency', 'std')]:.0f}ms")
        print(f"      Success Rate: {success_rate:.3f}%")

    print(f"\n🎯 Service Tier Comparison (All Regions):")
    tier_stats = df.groupby('tier')['avg_server_latency'].agg(['mean', 'std']).round(2)
    for tier in ['flex', 'default', 'priority']:
        if tier in tier_stats.index:
            print(f"   {tier.upper()}: {tier_stats.loc[tier, 'mean']:.0f}ms (±{tier_stats.loc[tier, 'std']:.0f}ms)")

    print(f"\n⚡ Concurrency Impact (Default Tier):")
    concurrency_stats = df[df['tier'] == 'default'].groupby('concurrency')['avg_server_latency'].mean().round(2)
    for conc, latency in concurrency_stats.items():
        print(f"   Concurrency {conc}: {latency:.0f}ms")

    print(f"\n💰 Token Consumption:")
    total_input = df['avg_input_tokens'].sum()
    total_output = df['avg_output_tokens'].sum()
    print(f"   Total Input Tokens: {total_input:,.0f}")
    print(f"   Total Output Tokens: {total_output:,.0f}")
    print(f"   Total Tokens: {(total_input + total_output):,.0f}")

    print("\n" + "="*80)

def main():
    print("🚀 Loading multi-region test data...")
    df = load_all_data()

    print(f"\n✅ Loaded {len(df):,} total records from {df['region'].nunique()} regions")
    print(f"   Regions: {', '.join(df['region'].unique())}")
    print(f"   Concurrency Levels: {sorted(df['concurrency'].unique())}")
    print(f"   Service Tiers: {sorted(df['tier'].unique())}")

    print("\n📊 Generating charts...")
    plot_latency_by_region_and_tier(df)
    plot_latency_by_concurrency(df)
    plot_latency_timeline(df)
    plot_success_rate(df)
    plot_tier_comparison_heatmap(df)
    plot_token_statistics(df)
    plot_latency_distribution(df)

    generate_summary_report(df)

    print("\n✅ All charts generated successfully!")
    print("📁 Charts saved in: /home/ubuntu/codes/nova/performance/")

if __name__ == "__main__":
    main()

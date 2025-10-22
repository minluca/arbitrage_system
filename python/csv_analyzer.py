import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import sys

def analyze_arbitrage_results(csv_file):
    df = pd.read_csv(csv_file)
    
    print("=" * 60)
    print(f"ARBITRAGE DETECTION - RESULTS ANALYSIS")
    print(f"Dataset: {csv_file}")
    print("=" * 60)
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['profit_pct'] = (df['profit_factor'] - 1) * 100
    duration = (df['timestamp'].max() - df['timestamp'].min()).total_seconds()
    
    print(f"\n📊 EXECUTIVE SUMMARY")
    total_arbs = len(df)
    high_profit_arbs = df[df['profit_pct'] > 0.5]
    print(f"  Duration: {duration/60:.1f} minutes ({duration:.0f}s)")
    print(f"  Total arbitrages: {total_arbs}")
    print(f"  Arbitrages with profit >0.5%: {len(high_profit_arbs)}")
    print(f"  Detection rate: {len(df)/duration:.3f} arb/s")
    
    intra = df[df['cycle_type'] == 'intra-exchange']
    cross = df[df['cycle_type'] == 'cross-exchange']
    print(f"\n🔄 CYCLE DISTRIBUTION")
    print(f"  Intra-exchange: {len(intra)} ({len(intra)/len(df)*100:.1f}%)")
    print(f"  Cross-exchange: {len(cross)} ({len(cross)/len(df)*100:.1f}%)")
    
    print(f"\n💰 TOP 10 HIGHEST PROFITS")
    top10 = df.nlargest(10, 'profit_pct')
    for i, row in top10.iterrows():
        print(f"  {i+1}. Profit: {row['profit_pct']:.4f}%, Path: {row.get('path', 'N/A')}")
    
    mean_profit_per_sec = df['profit_pct'].sum() / duration
    print(f"\n📈 AVERAGE PROFIT PER SECOND")
    print(f"  {mean_profit_per_sec:.6f}% per second")
    
    plt.style.use('seaborn-v0_8-darkgrid')
    fig, axes = plt.subplots(3, 1, figsize=(15, 15))
    
    bins = [0.5, 0.75, 1, 1.25, df['profit_pct'].max()]
    labels = ['0.5-0.75%', '0.75-1%', '1-1.25%', '>1.25%']
    df['profit_bin'] = pd.cut(df['profit_pct'], bins=bins, labels=labels, include_lowest=True)
    profit_counts = df['profit_bin'].value_counts().sort_index()
    axes[0].bar(profit_counts.index, profit_counts.values, edgecolor='black', alpha=0.7)
    axes[0].set_xlabel('Profit Range (%)')
    axes[0].set_ylabel('Number of Arbitrages')
    axes[0].set_title('Arbitrages per Profit Range')
    
    df['time_bin'] = df['timestamp'].dt.floor('30min')
    time_counts = df.groupby('time_bin').size()
    axes[1].bar(time_counts.index, time_counts.values, width=0.02, edgecolor='black')
    axes[1].set_xlabel('Time')
    axes[1].set_ylabel('Number of Arbitrages')
    axes[1].set_title('Arbitrages per 30-min Interval')
    
    df.set_index('timestamp')['profit_pct'].resample('1min').mean().plot(ax=axes[2])
    axes[2].set_xlabel('Time')
    axes[2].set_ylabel('Average Profit (%)')
    axes[2].set_title('Average Profit Over Time (1-min avg)')
    
    plt.tight_layout()
    output_file = csv_file.replace('.csv', '_analysis.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n📈 Visualization saved: {output_file}")
    
    print("\n" + "=" * 60)
    print("Analysis complete!")
    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_results.py <csv_file>")
        sys.exit(1)
    
    analyze_arbitrage_results(sys.argv[1])

import pandas as pd
import numpy as np

# Read the CSV file with correct encoding
df = pd.read_csv('返佣文件.csv', encoding='utf-8')

# Create a list to store all rows
all_rows = []

# Process each UID
for uid in sorted(df['好友ID（现货）'].unique()):
    user_data = df[df['好友ID（现货）'] == uid]
    
    # Calculate total USDT rebate for this user
    total_usdt = user_data['返佣收入(USDT)'].sum()
    if total_usdt == 0:
        continue  # Skip users with no rebate
        
    # Add header row for this user
    all_rows.append({
        '现货UID': uid,
        '交易类型': '账户汇总',
        '返佣数量': '',
        '返佣币种': '',
        'USDT价值': f'{total_usdt:.8f}',
    })
    
    # Process USDT-futures
    usdt_futures = user_data[user_data['订单类型'] == 'USDT-futures']
    if len(usdt_futures) > 0:
        usdt_value = usdt_futures['返佣收入(USDT)'].sum()
        if usdt_value > 0:
            all_rows.append({
                '现货UID': uid,
                '交易类型': 'U本位合约',
                '返佣数量': f'{usdt_value:.8f}',
                '返佣币种': 'USDT',
                'USDT价值': f'{usdt_value:.8f}',
            })
    
    # Process other types
    type_map = {
        'Coin-futures': '币本位合约',
        'margin': '杠杆',
        'spot': '现货'
    }
    
    for order_type, type_name in type_map.items():
        type_data = user_data[user_data['订单类型'] == order_type]
        if len(type_data) > 0:
            # Group by asset
            assets = type_data.groupby('返佣资产').agg({
                '返佣收入': 'sum',
                '返佣收入(USDT)': 'sum'
            }).reset_index()
            
            for _, row in assets.iterrows():
                if float(row['返佣收入']) > 0:
                    all_rows.append({
                        '现货UID': uid,
                        '交易类型': type_name,
                        '返佣数量': f'{float(row["返佣收入"]):.8f}',
                        '返佣币种': row['返佣资产'],
                        'USDT价值': f'{row["返佣收入(USDT)"]:.8f}',
                    })
    
    # Add a blank row after each user
    all_rows.append({
        '现货UID': '',
        '交易类型': '',
        '返佣数量': '',
        '返佣币种': '',
        'USDT价值': '',
    })

# Convert to DataFrame
final_summary = pd.DataFrame(all_rows)

# Save the results with correct encoding
final_summary.to_csv('rebate_summary.csv', index=False, encoding='utf-8-sig')

# Display the results
pd.set_option('display.max_colwidth', None)
pd.set_option('display.max_rows', None)
print("\n返佣汇总:")
print(final_summary.to_string(index=False))

import json
import pandas as pd
from binance.spot import Spot
from binance.error import ClientError
import time
import logging
from decimal import Decimal, ROUND_DOWN
import requests
from functools import wraps
import random

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('transfer_log.txt'),
        logging.StreamHandler()
    ]
)

# 币安API配置
API_KEY = ''
API_SECRET = ''

def create_client():
    """创建币安API客户端"""
    return Spot(api_key=API_KEY, 
              api_secret=API_SECRET,
              base_url='https://api.binance.com',
              show_limit_usage=True,
              show_header=True)

def retry_with_new_client(max_retries=5):
    """每次重试都创建新的客户端"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    # 每次重试都创建新的客户端
                    client = create_client()
                    # 添加随机延迟
                    time.sleep(random.uniform(0.5, 1.0))
                    return func(client, *args, **kwargs)
                except ClientError as e:
                    if e.error_code == -1021 and attempt < max_retries - 1:  # 时间同步错误
                        logging.warning(f"时间同步错误，重试第 {attempt + 1} 次")
                        continue
                    raise
            return func(create_client(), *args, **kwargs)
        return wrapper
    return decorator

@retry_with_new_client()
def get_account_info(client):
    """获取账户信息"""
    try:
        response = client.account()
        logging.info(f"获取到的账户信息: {response}")
        return response
    except Exception as e:
        logging.error(f"获取账户信息时发生错误: {str(e)}")
        raise

@retry_with_new_client()
def withdraw_usdt(client, amount, address):
    """提现USDT"""
    try:
        params = {
            'coin': 'USDT',
            'address': address,
            'amount': amount,
            'network': 'BSC'
        }
        logging.info(f"准备提现，参数: {params}")
        result = client.withdraw(**params)
        logging.info(f"提现API响应: {result}")
        return result
    except Exception as e:
        logging.error(f"提现时发生错误: {str(e)}")
        raise

def load_address_mapping():
    """加载UID到BSC地址的映射"""
    try:
        with open('address_mapping.json', 'r', encoding='utf-8') as f:
            mapping = json.load(f)
            logging.info(f"加载到的地址映射: {mapping}")
            return mapping
    except FileNotFoundError:
        logging.error("地址映射文件不存在")
        return {}
    except json.JSONDecodeError:
        logging.error("地址映射文件格式错误")
        return {}

def calculate_transfer_amount(usdt_value):
    """计算实际转账金额 (USDT价值 / 30 * 25)"""
    try:
        amount = Decimal(str(usdt_value)) / Decimal('30') * Decimal('25')
        return float(amount.quantize(Decimal('0.00000001'), rounding=ROUND_DOWN))
    except Exception as e:
        logging.error(f"计算转账金额时出错: {e}")
        return 0

def transfer_usdt(uid, amount, address):
    """转账USDT到指定地址"""
    try:
        # 获取账户信息
        account_info = get_account_info()
        
        # 检查账户信息格式
        if not isinstance(account_info, dict):
            logging.error(f"账户信息格式错误，期望dict类型，实际类型: {type(account_info)}")
            logging.error(f"账户信息内容: {account_info}")
            return False
            
        # 检查data字段
        if 'data' not in account_info:
            logging.error("账户信息中没有data字段")
            logging.error(f"账户信息字段: {list(account_info.keys())}")
            return False
            
        account_data = account_info['data']
        
        # 检查balances字段
        if 'balances' not in account_data:
            logging.error("账户data中没有balances字段")
            logging.error(f"账户data字段: {list(account_data.keys())}")
            return False
            
        # 检查USDT余额
        usdt_balance = 0
        for asset in account_data['balances']:
            if asset['asset'] == 'USDT':
                usdt_balance = float(asset['free'])
                logging.info(f"当前USDT余额: {usdt_balance}")
                break
        else:
            logging.error("账户中没有USDT资产")
            return False
        
        if usdt_balance < amount:
            logging.error(f"账户USDT余额不足，当前余额: {usdt_balance} USDT，需要: {amount} USDT")
            return False
        
        # 提现USDT
        result = withdraw_usdt(amount, address)
        logging.info(f"转账成功 - UID: {uid}, 金额: {amount} USDT, 地址: {address}")
        logging.info(f"转账详情: {result}")
        return True
        
    except ClientError as e:
        logging.error(f"币安API错误: {e.error_code}, {e.error_message if hasattr(e, 'error_message') else str(e)}")
        return False
    except Exception as e:
        logging.error(f"转账时发生错误: {str(e)}")
        logging.error(f"错误类型: {type(e)}")
        import traceback
        logging.error(f"错误堆栈: {traceback.format_exc()}")
        return False

def main():
    # 加载地址映射
    address_mapping = load_address_mapping()
    if not address_mapping:
        logging.error("无法加载地址映射，退出程序")
        return

    # 读取返佣汇总数据
    try:
        df = pd.read_csv('rebate_summary.csv', encoding='utf-8-sig')
        logging.info(f"读取到的账户列表: {df['现货UID'].unique()}")
    except Exception as e:
        logging.error(f"读取返佣数据失败: {e}")
        return

    # 处理每个账户的转账
    successful_transfers = 0
    failed_transfers = 0
    skipped_transfers = 0

    for _, row in df.iterrows():
        try:
            if pd.isna(row['现货UID']):  # 跳过NaN值
                continue
            uid = str(int(float(row['现货UID'])))  # 转换为整数再转字符串，去掉小数点
        except (ValueError, TypeError):
            continue
            
        if row['交易类型'] != '账户汇总':
            continue

        logging.info(f"处理UID: {uid}")
        if uid not in address_mapping:
            logging.info(f"跳过UID {uid}: 未找到对应的BSC地址")
            skipped_transfers += 1
            continue

        usdt_value = float(row['USDT价值'])
        transfer_amount = calculate_transfer_amount(usdt_value)
        
        if transfer_amount < 1:  # 小于1 USDT的转账跳过
            logging.info(f"跳过UID {uid}: 转账金额 {transfer_amount} USDT 小于最小限额")
            skipped_transfers += 1
            continue

        logging.info(f"准备转账: UID {uid}, 金额 {transfer_amount} USDT")
        if transfer_usdt(uid, transfer_amount, address_mapping[uid]):
            successful_transfers += 1
            time.sleep(1)  # 添加延迟避免API限制
        else:
            failed_transfers += 1

    # 输出统计信息
    logging.info(f"\n转账统计:")
    logging.info(f"成功: {successful_transfers}")
    logging.info(f"失败: {failed_transfers}")
    logging.info(f"跳过: {skipped_transfers}")

if __name__ == "__main__":
    main()

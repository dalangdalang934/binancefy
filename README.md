# 币安返佣转账脚本使用说明

## 功能概述
该脚本用于自动处理币安返佣的USDT转账操作。它能够读取返佣汇总数据，并根据配置的地址映射，自动将USDT转账到指定的BSC地址。

## 前置要求
1. 币安API密钥（需要开通提现权限）
2. Python 3.x
3. 必要的Python包：
   - binance-connector
   - pandas
   - requests
   - decimal

## 安装必要库
使用以下命令安装所需的Python包：
```bash
pip install binance-connector-python pandas requests
```

## 配置文件说明

### 1. transfer_rebate.py
主脚本文件，需要配置以下参数：
```python
API_KEY = ''    # 币安API Key
API_SECRET = '' # 币安API Secret
```

### 2. address_mapping.json
UID到BSC地址的映射文件，格式如下：
```json
{
    "用户UID": "BSC钱包地址",
    "12345": "0x1234..."
}
```

### 3. rebate_summary.csv
返佣汇总数据文件，必须包含以下列：
- 现货UID
- USDT价值
- 交易类型

## 转账规则
1. 仅处理"交易类型"为"账户汇总"的记录
2. 实际转账金额计算公式：USDT价值 / 30 * 25
3. 仅在账户USDT余额充足时执行转账
4. 使用BSC网络进行USDT转账

## 日志说明
脚本会生成 `transfer_log.txt` 日志文件，记录：
- 转账操作详情
- 错误信息
- 账户余额信息
- API调用结果

## 安全建议
1. 请妥善保管API密钥
2. 建议将API密钥存储在环境变量中
3. 定期检查日志文件确保转账正常
4. 建议先小额测试后再进行大额转账

## 错误处理
脚本包含以下错误处理机制：
1. API调用自动重试（最多5次）
2. 时间同步自动处理
3. 详细的错误日志记录
4. 余额不足保护

## 使用步骤
1. 配置API密钥
2. 准备address_mapping.json文件
3. 准备rebate_summary.csv文件
4. 运行脚本：
```bash
python zhuanzhang.py
```

## 注意事项
1. 确保API密钥有提现权限
2. 确保BSC地址格式正确
3. 建议在正式运行前进行小额测试
4. 定期检查日志文件
5. 保持币安现货账户有足够的USDT余额
6. 转账钱使用1.py来处理返佣数据
7. 感觉好用的大佬可以给我打赏,来者不拒:0xb707c50f09e667f55e760b0bc4b4777777777777
8. 联系方式tg:@Oxeeewct 推特:@DaWitThink

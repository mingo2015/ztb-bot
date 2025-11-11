# ztb_auto.py - 涨停板 + 龙虎榜自动分析（美西时间优化）
import requests
import akshare as ak
from datetime import datetime, timedelta
import os

# ========= 配置微信推送 =========
PUSH_TOKEN = os.environ.get("PUSH_TOKEN")  # GitHub Secrets 会自动注入

def push_wechat(title, content):
    if not PUSH_TOKEN:
        print("PUSH_TOKEN 未设置，跳过推送")
        return
    url = f"https://sctapi.ftqq.com/{PUSH_TOKEN}.send"
    data = {"title": title, "desp": content}
    try:
        requests.post(url, data=data)
        print("微信推送成功")
    except:
        print("推送失败")

# ========= 美西时间转换 =========
beijing_time = datetime.now() + timedelta(hours=16)  # UTC+8
pst_time = datetime.now() - timedelta(hours=8)       # UTC-8
date_str = beijing_time.strftime("%Y%m%d")

# ========= 获取涨停板 =========
try:
    df_zt = ak.stock_zt_pool_em(date=date_str)
except:
    push_wechat("❌ 涨停数据获取失败", "请检查网络或稍后重试")
    exit()

# ========= 主报告 =========
report = f"# 📊 涨停板自动简报\n\n"
report += f"**美西时间**：{pst_time.strftime('%Y-%m-%d %I:%M %p PST')}\n"
report += f"**对应A股**：{beijing_time.strftime('%Y-%m-%d')} 收盘\n\n"

if df_zt.empty:
    report += "> 今日无涨停板\n"
else:
    for _, row in df_zt.head(5).iterrows():  # 只取前5只
        code = row['代码']
        name = row['名称']
        try:
            # 简易强度评分
            score = 0
            if '集合金额' in row and row['集合金额'] > 5000: score += 30
            if '量比' in row and row['量比'] > 10: score += 20
            if '流通市值' in row and row['流通市值'] < 20: score += 20
            if '封单金额' in row and row['封单金额'] > 10000: score += 30
            score = min(score, 100)

            # 龙虎榜简判
            lhb_tag = "🟡 待分析"
            try:
                df_lhb = ak.stock_lhb_detail_em(date=date_str, symbol=code[:6])
                if not df_lhb.empty:
                    net_buy = df_lhb['买入金额'].sum() - df_lhb['卖出金额'].sum()
                    if net_buy > 1e8: lhb_tag = "🟢 真龙"
                    elif df_lhb.iloc[0]['营业部名称'] == df_lhb.iloc[-1]['营业部名称']: lhb_tag = "🚨 对倒"
            except:
                pass

            suggest = "低吸" if score > 80 else "观察" if score > 60 else "回避"
            report += f"### {code} {name}\n- 强度：`{score}分` | {lhb_tag}\n- 建议：**{suggest}**\n\n"
        except:
            report += f"### {code} {name}\n- 数据解析失败\n\n"

# ========= 发送报告 =========
push_wechat("📈 今日涨停自动分析", report)
print("任务完成，报告已生成")

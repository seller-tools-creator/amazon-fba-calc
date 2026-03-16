import streamlit as st
import requests
import re
import pandas as pd
import io

# ===================== 万邦1688 API 配置 =====================
ONEBOUND_KEY = "t9128954480"
ONEBOUND_SECRET = "4480ca0a"

# ===================== 亚马逊品类佣金表 =====================
CATEGORY_REFERRAL = {
    "宠物用品": 0.15,
    "家居/家具": 0.15,
    "厨房用品": 0.15,
    "户外用品": 0.15,
    "运动产品": 0.15,
    "美妆个护": 0.10,
    "服装/鞋靴": 0.17,
    "3C电子/手机配件": 0.08,
    "家电": 0.08,
    "图书": 0.15,
    "玩具": 0.15,
    "自定义(手动输入)": None
}

# ===================== 精准提取1688商品ID =====================
def extract_num_iid(url_or_iid):
    s = str(url_or_iid).strip()
    if s.isdigit():
        return s
    pattern = r'detail\.1688\.com/offer/(\d+)\.html'
    match = re.search(pattern, s)
    return match.group(1) if match else None

# ===================== 获取1688商品信息 =====================
def get_1688_item(num_iid):
    url = "https://api-gw.onebound.cn/1688/item_get/"
    params = {
        "key": ONEBOUND_KEY,
        "secret": ONEBOUND_SECRET,
        "num_iid": num_iid,
        "cache": "no",
        "lang": "zh-CN"
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("error"):
            st.error(f"API调用失败：{data.get('error')}")
            return None
        return data.get("item", {})
    except Exception as e:
        st.error(f"网络请求失败：{str(e)}")
        return None

# ===================== 自动估算美国站FBA费用 =====================
def estimate_fba_us(weight_kg):
    oz = weight_kg * 35.274
    if oz <= 3.53:
        return 3.53
    elif oz <= 12.5:
        return 4.15
    elif oz <= 25:
        return 4.96
    elif oz <= 50:
        return 6.48
    elif oz <= 100:
        return 8.19
    else:
        return 10.90

# ===================== 完整利润计算 =====================
def calc_profit(
    price_usd, cost_cny, weight_kg,
    rate=7.25,
    referral_rate=0.15,
    shipping_usd_per_unit=0.0,
    ad_enabled=False, ad_fee_usd=0.0,
    brand_enabled=False, brand_fee_usd=0.0,
    return_enabled=False, return_rate=0.0
):
    fba_usd = estimate_fba_us(weight_kg)
    cost_usd = cost_cny / rate
    referral_fee = price_usd * referral_rate
    total_cost = cost_usd + fba_usd + referral_fee + shipping_usd_per_unit

    ad_cost = ad_fee_usd if ad_enabled else 0.0
    brand_cost = brand_fee_usd if brand_enabled else 0.0
    total_cost += ad_cost + brand_cost

    profit_before_return = price_usd - total_cost
    return_loss = (price_usd * return_rate) if return_enabled else 0.0
    final_profit = profit_before_return - return_loss
    margin = final_profit / price_usd if price_usd != 0 else 0
    roi = final_profit / total_cost if total_cost != 0 else 0

    return {
        "售价USD": round(price_usd, 2),
        "1688成本CNY": round(cost_cny, 2),
        "成本USD": round(cost_usd, 2),
        "佣金比例": f"{referral_rate:.1%}",
        "佣金USD": round(referral_fee, 2),
        "FBA费用USD": round(fba_usd, 2),
        "头程运费USD": round(shipping_usd_per_unit, 2),
        "广告费USD": round(ad_cost, 2),
        "品牌费USD": round(brand_cost, 2),
        "退货损失USD": round(return_loss, 2),
        "总成本USD": round(total_cost, 2),
        "最终净利润USD": round(final_profit, 2),
        "净利率": f"{margin:.1%}",
        "ROI": f"{roi:.1%}"
    }

# ===================== 页面样式：标签拉宽 =====================
st.set_page_config(page_title="亚马逊FBA利润计算器", layout="wide")

st.markdown("""
<style>
/* 让两个标签页铺满、各占50% */
.stTabs [data-testid="stMarkdownContainer"] {
    width: 100%;
}
.stTabs [role="tablist"] {
    display: flex;
}
.stTabs [role="tab"] {
    flex: 1;
    font-size: 18px;
    padding: 12px 0;
}
</style>
""", unsafe_allow_html=True)

st.title("📦 1688 → 亚马逊美国站 FBA 精准利润计算器")

tab1, tab2 = st.tabs(["🔍 单品计算", "📊 批量计算"])

# ==============================================
# 标签页1：单品计算
# ==============================================
with tab1:
    st.subheader("单品利润计算")
    st.caption("支持：1688官方链接 / 纯商品ID")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        input_url = st.text_input("输入1688商品链接/纯ID", placeholder="例：https://detail.1688.com/offer/617755177439.html", key="single_url")
    with col2:
        price_usd = st.number_input("亚马逊售价 USD", value=29.99, key="single_price")
    
    col3, col4, col5 = st.columns(3)
    with col3:
        category = st.selectbox("商品品类（自动佣金）", list(CATEGORY_REFERRAL.keys()), index=0, key="single_category")
        if CATEGORY_REFERRAL[category] is not None:
            referral_rate = CATEGORY_REFERRAL[category]
            st.caption(f"✅ 自动佣金：{referral_rate:.1%}")
        else:
            referral_rate = st.number_input("自定义佣金比例", value=0.15, key="single_referral")
    with col4:
        rate = st.number_input("汇率（CNY→USD）", value=7.25, key="single_rate")
    with col5:
        shipping = st.number_input("头程运费/个 USD", value=1.5, key="single_shipping")

    st.markdown("---")
    st.caption("可选费用（勾选启用）")
    col6, col7, col8 = st.columns(3)
    with col6:
        ad_on = st.checkbox("广告费", key="single_ad_check")
        ad_fee = st.number_input("广告费/个 USD", value=1.0, disabled=not ad_on, key="single_ad_fee")
    with col7:
        brand_on = st.checkbox("品牌费", key="single_brand_check")
        brand_fee = st.number_input("品牌费/个 USD", value=0.5, disabled=not brand_on, key="single_brand_fee")
    with col8:
        ret_on = st.checkbox("退货率", key="single_ret_check")
        ret_rate = st.number_input("退货率 %", value=5.0, disabled=not ret_on, key="single_ret_rate") / 100

    warn_profit = st.number_input("净利润预警阈值（USD）", value=3.0, key="single_warn")

    # 按钮恢复原来样式，去掉 primary
    if st.button("✅ 抓取并计算利润", key="single_calc_btn"):
        if not input_url:
            st.warning("请输入1688商品链接或纯ID！")
        else:
            num_iid = extract_num_iid(input_url)
            if not num_iid:
                st.error("❌ 无法识别商品ID！请检查链接是否为1688官方格式")
            else:
                st.info(f"✅ 识别商品ID：{num_iid}")
                with st.spinner("正在从1688抓取商品信息..."):
                    item = get_1688_item(num_iid)

                if item and item.get("title"):
                    st.success("✅ 商品信息抓取成功！")
                    with st.expander("📄 商品详情", expanded=True):
                        col9, col10, col11 = st.columns(3)
                        with col9:
                            st.markdown(f"**商品名称**：{item.get('title', '')[:80]}...")
                        with col10:
                            st.markdown(f"**1688采购价**：{item.get('price', '0')} 元/个")
                        with col11:
                            st.markdown(f"**商品重量**：{item.get('weight', '0.2')} kg")

                    try:
                        cost_cny = float(item.get("price", 0))
                    except:
                        cost_cny = 0.0
                    try:
                        weight_kg = float(item.get("weight", 0.2))
                    except:
                        weight_kg = 0.2

                    result = calc_profit(
                        price_usd=price_usd,
                        cost_cny=cost_cny,
                        weight_kg=weight_kg,
                        rate=rate,
                        referral_rate=referral_rate,
                        shipping_usd_per_unit=shipping,
                        ad_enabled=ad_on,
                        ad_fee_usd=ad_fee,
                        brand_enabled=brand_on,
                        brand_fee_usd=brand_fee,
                        return_enabled=ret_on,
                        return_rate=ret_rate
                    )

                    final_profit = result["最终净利润USD"]
                    st.subheader("💰 最终利润计算结果")
                    if final_profit < warn_profit:
                        st.error(f"⚠️ 利润过低：${final_profit} ＜ 预警线 ${warn_profit}")
                    else:
                        st.success(f"✅ 利润合格：${final_profit} ≥ ${warn_profit}")

                    col12, col13 = st.columns(2)
                    with col12:
                        st.metric("售价USD", result["售价USD"])
                        st.metric("1688成本CNY", result["1688成本CNY"])
                        st.metric("成本USD", result["成本USD"])
                        st.metric("佣金USD", result["佣金USD"])
                        st.metric("FBA费用USD", result["FBA费用USD"])
                    with col13:
                        st.metric("头程运费USD", result["头程运费USD"])
                        st.metric("广告费USD", result["广告费USD"])
                        st.metric("品牌费USD", result["品牌费USD"])
                        st.metric("总成本USD", result["总成本USD"])
                        st.metric("最终净利润USD", result["最终净利润USD"])
                    st.metric("净利率", result["净利率"])
                    st.metric("ROI", result["ROI"])
                else:
                    st.error("❌ 商品信息抓取失败")

# ==============================================
# 标签页2：批量计算
# ==============================================
with tab2:
    st.subheader("批量Excel利润计算")
    st.caption("Excel：第1列=链接/ID，第2列=售价USD")
    
    uploaded_file = st.file_uploader("上传Excel文件", type=["xlsx"], key="batch_upload")
    
    col14, col15, col16 = st.columns(3)
    with col14:
        batch_rate = st.number_input("汇率（CNY→USD）", value=7.25, key="batch_rate")
    with col15:
        batch_category = st.selectbox("批量商品品类", list(CATEGORY_REFERRAL.keys()), index=0, key="batch_category")
        if CATEGORY_REFERRAL[batch_category] is not None:
            batch_referral = CATEGORY_REFERRAL[batch_category]
            st.caption(f"✅ 自动佣金：{batch_referral:.1%}")
        else:
            batch_referral = st.number_input("批量自定义佣金", value=0.15, key="batch_referral")
    with col16:
        batch_ship = st.number_input("头程运费/个 USD", value=1.5, key="batch_shipping")

    st.markdown("---")
    st.caption("批量可选费用")
    col17, col18, col19 = st.columns(3)
    with col17:
        b_ad_on = st.checkbox("启用广告费", key="batch_ad_check")
        b_ad = st.number_input("广告费/个 USD", value=1.0, disabled=not b_ad_on, key="batch_ad_fee")
    with col18:
        b_brand_on = st.checkbox("启用品牌费", key="batch_brand_check")
        b_brand = st.number_input("品牌费/个 USD", value=0.5, disabled=not b_brand_on, key="batch_brand_fee")
    with col19:
        b_ret_on = st.checkbox("启用退货率", key="batch_ret_check")
        b_ret = st.number_input("退货率 %", value=5.0, disabled=not b_ret_on, key="batch_ret_rate") / 100

    batch_warn = st.number_input("批量净利润预警阈值（USD）", value=3.0, key="batch_warn")

    # 按钮恢复原来样式
    if uploaded_file and st.button("🚀 开始批量计算", key="batch_calc_btn"):
        try:
            df = pd.read_excel(uploaded_file, header=None)
            id_col = 0
            price_col = 1
            st.info(f"✅ 商品列：第{id_col+1}列 | 售价列：第{price_col+1}列")

            result_list = []
            total = len(df)
            progress_bar = st.progress(0)
            fail_count = 0

            for idx, row in df.iterrows():
                iid_str = str(row[id_col])
                price = row[price_col]
                num_iid = extract_num_iid(iid_str)
                if not num_iid:
                    fail_count +=1
                    progress_bar.progress((idx + 1) / total)
                    continue

                item = get_1688_item(num_iid)
                if not item or not item.get("title"):
                    fail_count +=1
                    progress_bar.progress((idx + 1) / total)
                    continue

                try:
                    cost = float(item.get("price", 0))
                    weight = float(item.get("weight", 0.2))
                except:
                    cost = 0.0
                    weight = 0.2

                res = calc_profit(
                    price_usd=price,
                    cost_cny=cost,
                    weight_kg=weight,
                    rate=batch_rate,
                    referral_rate=batch_referral,
                    shipping_usd_per_unit=batch_ship,
                    ad_enabled=b_ad_on,
                    ad_fee_usd=b_ad,
                    brand_enabled=b_brand_on,
                    brand_fee_usd=b_brand,
                    return_enabled=b_ret_on,
                    return_rate=b_ret
                )

                result_list.append({
                    "1688商品ID": num_iid,
                    "商品标题": item.get("title", "")[:60] + "...",
                    "1688采购价(CNY)": item.get("price", 0),
                    "商品重量(kg)": item.get("weight", 0.2),
                    **res
                })
                progress_bar.progress((idx + 1) / total)

            if result_list:
                out_df = pd.DataFrame(result_list)
                st.success(f"✅ 完成 {len(result_list)} 个 | 失败 {fail_count} 个")

                def highlight_low(row):
                    return ["background-color: #ffebee" if row["最终净利润USD"] < batch_warn else "" for _ in row]
                styled_df = out_df.style.apply(highlight_low, axis=1)
                st.dataframe(styled_df, use_container_width=True, height=400)

                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    out_df.to_excel(writer, index=False)
                buffer.seek(0)
                st.download_button("📥 下载结果", buffer, "批量利润结果.xlsx", key="batch_download")
            else:
                st.warning("❌ 无有效商品")
        except Exception as e:
            st.error(f"错误：{str(e)}")

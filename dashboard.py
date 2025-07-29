import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go # 新增 go，用於更底層的繪圖
import numpy as np
import io # 新增 io 模組，用於數據下載

# --- 設定頁面 --- 
st.set_page_config(
    page_title="帳齡分析儀表板",
    page_icon="📊",
    layout="wide"
)

# --- 讀取和準備資料 ---
DATA_FILE = 'consolidated_report_long.csv'

@st.cache_data
def load_data():
    try:
        df = pd.read_csv(DATA_FILE)
        if '合約日期' in df.columns:
            # 嘗試將合約日期轉換為日期時間物件，如果格式不符則設為 NaT
            df['合約日期'] = pd.to_datetime(df['合約日期'], format='%Y/%m', errors='coerce')
            # 移除無法轉換的日期行
            df.dropna(subset=['合約日期'], inplace=True)
        if '月份' in df.columns:
            # 嘗試將月份轉換為日期時間物件，如果格式不符則設為 NaT
            df['月份'] = pd.to_datetime(df['月份'], format='%Y/%m', errors='coerce')
            # 移除無法轉換的月份行
            df.dropna(subset=['月份'], inplace=True)
        if '案件編號' in df.columns:
            df['案件編號'] = df['案件編號'].astype(str)

        if '帳齡' in df.columns:
            aging_order = ['M6+', 'M6', 'M5', 'M4', 'M3', 'M2', 'M1', 'M0', 'Normal']
            df['帳齡'] = pd.Categorical(df['帳齡'], categories=aging_order, ordered=True)
            df.dropna(subset=['帳齡'], inplace=True)

        return df
    except FileNotFoundError:
        st.error(f"錯誤：找不到資料檔案 '{DATA_FILE}'。請確認檔案是否與腳本在同一個資料夾中。")
        return None

df = load_data()

# --- 圖表生成函式 ---
def create_heatmap(filtered_df, title_text, heatmap_mode, use_log_scale, heatmap_order):
    pivot_df = pd.pivot_table(
        filtered_df, values='案件編號', index='帳齡', 
        columns='月份', aggfunc='count', fill_value=0, observed=False
    ).reindex(heatmap_order, fill_value=0)

    if heatmap_mode == '案件佔比 (%)':
        heatmap_data = pivot_df.div(pivot_df.sum(axis=0), axis=1).multiply(100)
        text_template = "%{text:.1f}%"
        text_data = heatmap_data
        color_scale_label = "佔比 (%)"
    else:
        heatmap_data = pivot_df
        text_template = "%{text}"
        text_data = heatmap_data
        color_scale_label = "案件數量"

    color_data = heatmap_data
    if use_log_scale:
        color_data = heatmap_data.apply(lambda x: np.log1p(x))
        title_text += " (對數色階)"

    fig = go.Figure(data=go.Heatmap(
        z=color_data,
        x=pivot_df.columns,
        y=pivot_df.index,
        text=text_data.round(2),
        texttemplate=text_template,
        textfont={"size":10},
        colorscale='YlOrRd',
        colorbar_title_text=color_scale_label
    ))
    fig.update_layout(title_text=title_text)
    if use_log_scale:
        fig.update_layout(coloraxis_showscale=False)
    return fig

def create_violin_chart(filtered_df, title_text, other_charts_order):
    fig = px.violin(
        filtered_df, x='月份', y='帳齡', title=title_text,
        box=True, points='all', labels={'月份': '檢視月份', '帳齡': '帳齡分類'},
        category_orders={'帳齡': other_charts_order}
    )
    return fig

def create_box_chart(filtered_df, title_text, other_charts_order):
    fig = px.box(
        filtered_df, x='月份', y='帳齡', title=title_text,
        points='all', labels={'月份': '檢視月份', '帳齡': '帳齡分類'},
        category_orders={'帳齡': other_charts_order}
    )
    return fig

def create_scatter_chart(filtered_df, title_text, other_charts_order):
    fig = px.scatter(
        filtered_df, x='月份', y='帳齡', title=title_text,
        color='案件編號', labels={'月份': '檢視月份', '帳齡': '帳齡分類'},
        category_orders={'帳齡': other_charts_order}
    )
    return fig

def create_line_chart(filtered_df, title_text, filter_type, other_charts_order):
    fig = px.line(
        filtered_df, x='月份', y='帳齡', title=title_text,
        color='案件編號' if '依合約日期範圍篩選' in filter_type else None, 
        markers=True, labels={'月份': '檢視月份', '帳齡': '帳齡分類'},
        category_orders={'帳齡': other_charts_order}
    )
    return fig

def create_stacked_bar_chart(filtered_df, title_text, other_charts_order, stacked_bar_mode):
    # 計算每個月份各帳齡的案件數量
    df_grouped = filtered_df.groupby(['月份', '帳齡']).size().reset_index(name='案件數量')
    
    # 確保月份排序正確
    df_grouped['月份'] = pd.Categorical(df_grouped['月份'], categories=sorted(filtered_df['月份'].unique()), ordered=True)
    df_grouped = df_grouped.sort_values('月份')

    if stacked_bar_mode == '案件佔比 (%)':
        # 計算每個月份的總案件數
        total_cases_per_month = df_grouped.groupby('月份')['案件數量'].transform('sum')
        # 計算佔比
        df_grouped['案件佔比'] = (df_grouped['案件數量'] / total_cases_per_month) * 100
        y_col = '案件佔比'
        y_title = '案件佔比 (%)'
        hover_data = {'案件數量': True, '案件佔比': ':.2f'}
        chart_title = f"{title_text} - 案件佔比 (%)"
    else:
        y_col = '案件數量'
        y_title = '案件數量'
        hover_data = {'案件數量': True}
        chart_title = f"{title_text} - 案件數量"

    fig = px.bar(
        df_grouped, 
        x='月份', 
        y=y_col, 
        color='帳齡', 
        title=chart_title,
        category_orders={'帳齡': other_charts_order}, # 確保帳齡順序正確
        labels={'月份': '檢視月份', y_col: y_title, '帳齡': '帳齡分類'},
        hover_data=hover_data
    )
    fig.update_layout(barmode='stack') # 堆疊模式
    return fig

def prepare_monthly_deterioration_data(df, selected_delay_categories, metric_name):
    # 計算每個月份的 selected_delay_categories 逾期案件數和總案件數
    df_copy = df.copy()
    df_copy['月份'] = pd.to_datetime(df_copy['月份']) # 確保月份是 datetime 類型

    # 計算每個月份的總案件數
    total_cases_per_month = df_copy.groupby('月份')['案件編號'].nunique().reset_index(name='總案件數')

    # 計算每個月份的 selected_delay_categories 逾期案件數
    delayed_cases_per_month = df_copy[df_copy['帳齡'].isin(selected_delay_categories)].groupby('月份')['案件編號'].nunique().reset_index(name=f'{metric_name}_逾期案件數')

    # 合併數據
    monthly_summary = pd.merge(total_cases_per_month, delayed_cases_per_month, on='月份', how='left').fillna(0)

    # 計算 selected_delay_categories 逾期比例
    monthly_summary[f'{metric_name}_逾期比例'] = (monthly_summary[f'{metric_name}_逾期案件數'] / monthly_summary['總案件數']) * 100
    monthly_summary.replace([np.inf, -np.inf], np.nan, inplace=True) # 處理除以零的無限值
    monthly_summary.dropna(subset=[f'{metric_name}_逾期比例'], inplace=True) # 移除 NaN 值

    # 按照月份排序
    monthly_summary = monthly_summary.sort_values(by='月份')

    # 計算月對月變化 (惡化指標)
    monthly_summary[f'月對月_{metric_name}_逾期比例變化'] = monthly_summary[f'{metric_name}_逾期比例'].diff()

    # 提取年份和月份數字
    monthly_summary['年份'] = monthly_summary['月份'].dt.year
    monthly_summary['月份數字'] = monthly_summary['月份'].dt.month

    return monthly_summary

def create_cohort_line_chart(filtered_df, title_text, selected_delay_metric_name):
    fig = px.line(
        filtered_df, 
        x='月份', 
        y='延滯比例', 
        color='合約月份', 
        title=title_text,
        markers=True,
        labels={'月份': '檢視月份', '延滯比例': selected_delay_metric_name, '合約月份': '合約月份'},
        hover_name='合約月份',
        line_shape="linear" # 可以是 "linear", "spline", "hv", "vh", "hvh"
    )
    fig.update_layout(
        yaxis_tickformat=".2f%", # 格式化Y軸為百分比
        hovermode="x unified"
    )
    return fig

def create_deterioration_boxplot(df_deterioration, metric_name):
    fig = px.box(
        df_deterioration,
        x='月份數字',
        y=f'月對月_{metric_name}_逾期比例變化',
        title=f'各月份資產品質惡化程度分佈 (月對月 {metric_name} 逾期比例變化)',
        labels={'月份數字': '月份', f'月對月_{metric_name}_逾期比例變化': f'{metric_name} 逾期比例變化 (%)'},
        points="all" # 顯示所有數據點
    )
    fig.update_layout(
        xaxis = dict(
            tickmode = 'array',
            tickvals = list(range(1, 13)),
            ticktext = [str(i) for i in range(1, 13)]
        )
    )
    return fig

def create_deterioration_heatmap(df_deterioration, metric_name):
    # 創建熱力圖所需的 pivot table
    pivot_df = df_deterioration.pivot_table(
        index='年份',
        columns='月份數字',
        values=f'月對月_{metric_name}_逾期比例變化'
    )
    
    # 確保月份順序正確
    pivot_df = pivot_df.reindex(columns=list(range(1, 13)))

    fig = go.Figure(data=go.Heatmap(
        z=pivot_df.values,
        x=pivot_df.columns,
        y=pivot_df.index.astype(str), # 將年份轉換為字串，避免浮點數顯示
        colorscale='RdYlGn_r', # 紅黃綠反轉色階，紅色代表惡化，綠色代表改善
        colorbar_title_text=f'{metric_name} 逾期比例變化 (%)',
        text=pivot_df.round(2).values, # 顯示數值
        texttemplate="%{text:.2f}",
        textfont={"size":10}
    ))
    fig.update_layout(
        title_text=f'各年份各月份資產品質惡化程度熱力圖 (月對月 {metric_name} 逾期比例變化)',
        xaxis_title='月份',
        yaxis_title='年份'
    )
    return fig

if df is not None:
    st.title("📊 租車案件帳齡追蹤報表")
    st.markdown("使用側邊欄的篩選器來查看不同案件或合約日期的帳齡變化趨勢。")

    # 初始化可能未定義的變數
    selected_delay_metric_name = ""
    stacked_bar_mode = "案件數量" # 預設值
    heatmap_mode = "案件數量" # 預設值
    use_log_scale = False # 預設值

    # --- 側邊欄篩選器 ---
    st.sidebar.header("篩選項")

    filter_type = st.sidebar.radio(
        "請選擇篩選方式：",
        ('依合約日期範圍篩選', '依案件編號篩選', '依合約月份群組比較', '資產品質月變動分析'),
        help="選擇您想用來過濾資料的維度。"
    )

    chart_type = '折線圖' # 預設值

    if '依合約日期範圍篩選' in filter_type:
        # 預設圖表類型
        chart_type_options = ["熱力圖", "堆疊長條圖", "小提琴圖", "箱形圖", "散點圖", "折線圖"]
        chart_type = st.sidebar.selectbox(
            "選擇圖表類型:",
            chart_type_options,
            index=0, 
            help="熱力圖適合觀察整體數量分佈與變化，堆疊長條圖適合觀察月對月佔比變化，其他圖表適合觀察個別案件。"
        )

        if chart_type == "熱力圖":
            # 熱力圖只顯示單月數據，提供月份選擇
            all_contract_months = sorted(df['合約日期'].dt.strftime('%Y/%m').unique(), reverse=True)
            selected_date_str = st.sidebar.selectbox(
                '選擇合約月份 (YYYY/MM)', 
                all_contract_months,
                help="選擇一個合約月份，熱力圖將顯示該月簽約案件的帳齡分佈。"
            )
            start_date = pd.to_datetime(selected_date_str)
            end_date = start_date + pd.offsets.MonthEnd(0) # 獲取該月份的最後一天
            filtered_df = df[(df['合約日期'] >= start_date) & (df['合約日期'] <= end_date)]
            title_text = f"合約日期 {selected_date_str} 案件的帳齡 - 熱力圖"

            heatmap_mode = st.sidebar.radio(
                "熱力圖顯示模式:",
                ('案件數量', '案件佔比 (%)'),
                horizontal=True,
                help="顯示每個格子的絕對案件數，或佔當月總案件數的百分比。"
            )
            use_log_scale = st.sidebar.checkbox("增強低數量對比度 (對數模式)", value=True, help="當Normal案件數過多時，勾選此項可讓M1, M2等少量案件的顏色更明顯。")

        else:
            # 其他圖表類型，使用日期範圍選擇
            min_date = df['合約日期'].min().date()
            max_date = df['合約日期'].max().date()

            date_range = st.sidebar.date_input(
                "選擇合約日期範圍",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                help="選擇一個合約日期範圍，圖表將顯示所有在該範圍內簽約的案件。"
            )

            if len(date_range) == 2:
                start_date = pd.to_datetime(date_range[0])
                end_date = pd.to_datetime(date_range[1])
                filtered_df = df[(df['合約日期'] >= start_date) & (df['合約日期'] <= end_date)]
                title_text = f"合約日期從 {start_date.strftime('%Y/%m')} 到 {end_date.strftime('%Y/%m')} 的案件帳齡 - {chart_type}"
            else:
                filtered_df = pd.DataFrame() # 如果日期範圍不完整，則顯示空數據
                title_text = "請選擇完整的日期範圍"

            if chart_type == '堆疊長條圖':
                stacked_bar_mode = st.sidebar.radio(
                    "堆疊長條圖顯示模式:",
                    ('案件數量', '案件佔比 (%)'),
                    horizontal=True,
                    help="顯示每個月份各帳齡的絕對案件數，或佔當月總案件數的百分比。"
                )

    elif '依案件編號篩選' in filter_type:
        case_ids = sorted(df['案件編號'].unique())
        selected_case_ids = st.sidebar.multiselect(
            '選擇案件編號',
            case_ids,
            default=case_ids[0] if case_ids else [], # 預設選擇第一個案件，如果沒有則為空列表
            help="選擇一個或多個特定的案件編號來查看其帳齡歷史。"
        )

        if selected_case_ids:
            filtered_df = df[df['案件編號'].isin(selected_case_ids)]
            if len(selected_case_ids) == 1:
                contract_date_for_case = df[df['案件編號'] == selected_case_ids[0]]['合約日期'].dt.strftime('%Y/%m').iloc[0] if not filtered_df.empty else "N/A"
                title_text = f"案件 {selected_case_ids[0]} (合約日期: {contract_date_for_case}) 的帳齡趨勢"
            else:
                title_text = f"多個案件 ({len(selected_case_ids)} 個) 的帳齡趨勢"
        else:
            filtered_df = pd.DataFrame() # 如果沒有選擇案件，則顯示空數據
            title_text = "請選擇案件編號"
        chart_type = "折線圖"

    elif '依合約月份群組比較' in filter_type:
        all_contract_months = sorted(df['合約日期'].dt.strftime('%Y/%m').unique(), reverse=True)
        selected_contract_months = st.sidebar.multiselect(
            '選擇合約月份 (可多選)',
            all_contract_months,
            default=all_contract_months[:2] if len(all_contract_months) >= 2 else all_contract_months,
            help="選擇一個或多個合約月份，比較其資產包的延滯趨勢。"
        )

        delay_metric_options = {
            "M2+ 延滯比例": ['M2', 'M3', 'M4', 'M5', 'M6', 'M6+'],
            "M4+ 延滯比例": ['M4', 'M5', 'M6', 'M6+'],
            "M6+ 延滯比例": ['M6', 'M6+']
        }
        selected_delay_metric_name = st.sidebar.selectbox(
            '選擇延滯指標',
            list(delay_metric_options.keys()),
            help="選擇要追蹤的延滯指標（例如：M1+ 延滯比例）。"
        )
        selected_delay_categories = delay_metric_options[selected_delay_metric_name]

        if selected_contract_months:
            # 篩選出選定的合約月份數據
            filtered_df = df[df['合約日期'].dt.strftime('%Y/%m').isin(selected_contract_months)].copy()
            
            # 計算每個合約月份、每個月份的延滯比例
            # 總案件數 (以合約月份和檢視月份分組)
            total_cases_monthly = filtered_df.groupby([filtered_df['合約日期'].dt.strftime('%Y/%m').rename('合約月份'), '月份'])['案件編號'].nunique().reset_index(name='總案件數')
            
            # 延滯案件數
            delayed_cases_monthly = filtered_df[filtered_df['帳齡'].isin(selected_delay_categories)].groupby([filtered_df['合約日期'].dt.strftime('%Y/%m').rename('合約月份'), '月份'])['案件編號'].nunique().reset_index(name='延滯案件數')
            
            # 合併數據並計算比例
            merged_df = pd.merge(total_cases_monthly, delayed_cases_monthly, on=['合約月份', '月份'], how='left').fillna(0)
            merged_df['延滯比例'] = (merged_df['延滯案件數'] / merged_df['總案件數']) * 100
            
            # 確保月份排序正確
            merged_df['月份'] = pd.Categorical(merged_df['月份'], categories=sorted(merged_df['月份'].unique()), ordered=True)
            merged_df = merged_df.sort_values('月份')

            filtered_df = merged_df # 將處理後的數據賦值給 filtered_df
            title_text = f"不同合約月份資產包的 {selected_delay_metric_name} 趨勢"
            chart_type = "同期群折線圖" # 新增一個圖表類型標識
        else:
            filtered_df = pd.DataFrame()
            title_text = "請選擇合約月份"
        chart_type = "同期群折線圖"

    elif '資產品質月變動分析' in filter_type:
        st.sidebar.markdown("此分析將顯示各月份資產品質的月對月變化趨勢。")
        
        delay_metric_options_deterioration = {
            "M1+": ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M6+'],
            "M2+": ['M2', 'M3', 'M4', 'M5', 'M6', 'M6+'],
            "M4+": ['M4', 'M5', 'M6', 'M6+']
        }
        selected_delay_metric_name_deterioration = st.sidebar.selectbox(
            '選擇延滯指標',
            list(delay_metric_options_deterioration.keys()),
            help="選擇要追蹤的延滯指標（例如：M1+、M2+、M4+）。"
        )
        selected_delay_categories_deterioration = delay_metric_options_deterioration[selected_delay_metric_name_deterioration]

        chart_type_options = ["盒鬚圖", "熱力圖"]
        chart_type = st.sidebar.selectbox(
            "選擇圖表類型:",
            chart_type_options,
            index=0,
            help="盒鬚圖適合觀察各月份的整體分佈，熱力圖適合觀察跨年份的月份趨勢。"
        )
        # 準備數據
        filtered_df = prepare_monthly_deterioration_data(df.copy(), selected_delay_categories_deterioration, selected_delay_metric_name_deterioration)
        title_text = "資產品質月變動分析"


    # --- 主畫面圖表 ---
    # --- 關鍵指標 (KPIs) ---
    if not filtered_df.empty:
        if filter_type == '依合約月份群組比較':
            # 在同期群模式下，filtered_df 已經是聚合後的數據
            total_cases = filtered_df['總案件數'].sum()
            overdue_cases = filtered_df['延滯案件數'].sum()
            overdue_percentage = (overdue_cases / total_cases * 100) if total_cases > 0 else 0
        elif filter_type == '資產品質月變動分析':
            # 在資產品質月變動分析模式下，KPIs 不適用，或者需要重新定義
            total_cases = "N/A"
            overdue_cases = "N/A"
            overdue_percentage = "N/A"
        else:
            total_cases = filtered_df['案件編號'].nunique()
            overdue_aging_categories = ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M6+']
            overdue_cases = filtered_df[filtered_df['帳齡'].isin(overdue_aging_categories)]['案件編號'].nunique()
            overdue_percentage = (overdue_cases / total_cases * 100) if total_cases > 0 else 0

        st.subheader("關鍵指標")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="總案件數", value=total_cases)
        with col2:
            st.metric(label="逾期案件數 (M1+)", value=overdue_cases)
        with col3:
            st.metric(label="逾期案件佔比", value=f"{overdue_percentage:.2f}%" if isinstance(overdue_percentage, float) else overdue_percentage)
    else:
        st.info("請選擇篩選條件以顯示關鍵指標。")

    if not filtered_df.empty:
        # 只有在非資產品質月變動分析模式下才需要排序月份
        if filter_type != '資產品質月變動分析':
            filtered_df = filtered_df.sort_values(by='月份')

        # 【核心修正】定義兩套Y軸順序，以應對不同圖表的邏輯
        # 視覺順序：從下到上
        visual_order_base = ['Normal', 'M0', 'M1', 'M2', 'M3', 'M4', 'M5', 'M6+']
        other_charts_order = []
        heatmap_order = []
        
        # 只有在 filtered_df 包含 '帳齡' 欄位時才定義帳齡相關的順序
        if '帳齡' in filtered_df.columns:
            # 1. 給 px 圖表使用的順序 (px會將列表第一項放在最頂部)
            other_charts_order = [cat for cat in visual_order_base if cat in filtered_df['帳齡'].cat.categories][::-1]
            
            # 2. 給 go.Heatmap 使用的順序 (go.Heatmap會將列表第一項放在最底部)
            heatmap_order = [cat for cat in visual_order_base if cat in filtered_df['帳齡'].cat.categories]

        # 為 fig 提供一個預設值，以防沒有任何圖表被生成
        fig = go.Figure() 

        if chart_type == "熱力圖" and '依合約日期範圍篩選' in filter_type:
            fig = create_heatmap(filtered_df, title_text, heatmap_mode, use_log_scale, heatmap_order)

        elif chart_type == "堆疊長條圖":
            fig = create_stacked_bar_chart(filtered_df, title_text, other_charts_order, stacked_bar_mode)

        elif chart_type == "同期群折線圖":
            fig = create_cohort_line_chart(filtered_df, title_text, selected_delay_metric_name)

        elif chart_type == "小提琴圖":
            fig = create_violin_chart(filtered_df, title_text, other_charts_order)
        elif chart_type == "箱形圖":
            fig = create_box_chart(filtered_df, title_text, other_charts_order)
        elif chart_type == "散點圖":
            fig = create_scatter_chart(filtered_df, title_text, other_charts_order)
        elif chart_type == "折線圖":
            fig = create_line_chart(filtered_df, title_text, filter_type, other_charts_order)
        
        elif chart_type == "盒鬚圖" and '資產品質月變動分析' in filter_type:
            fig = create_deterioration_boxplot(filtered_df, selected_delay_metric_name_deterioration)
        elif chart_type == "熱力圖" and '資產品質月變動分析' in filter_type:
            fig = create_deterioration_heatmap(filtered_df, selected_delay_metric_name_deterioration)

        fig.update_layout(
            xaxis_title="<b>檢視月份</b>" if filter_type != '資產品質月變動分析' else "<b>月份</b>",
            yaxis_title="<b>案件數量</b>" if chart_type == "堆疊長條圖" else (
                "<b>" + selected_delay_metric_name + "</b>" if chart_type == "同期群折線圖" else (
                    "<b>" + selected_delay_metric_name_deterioration + " 逾期比例變化 (%)</b>" if filter_type == '資產品質月變動分析' else "<b>帳齡分類</b>"
                )
            ),
            title_font_size=20,
            hovermode="x unified"
        )

        st.plotly_chart(fig, use_container_width=True)

        with st.expander("查看篩選後的原始資料"):
            if chart_type == "同期群折線圖":
                st.dataframe(filtered_df.sort_values(by=['合約月份', '月份']))
            elif filter_type == '資產品質月變動分析':
                st.dataframe(filtered_df.sort_values(by=['年份', '月份數字']))
            else:
                st.dataframe(filtered_df.sort_values(by=['月份', '帳齡']))
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="下載篩選後的數據 (CSV)",
                data=csv,
                file_name="filtered_aging_report.csv",
                mime="text/csv",
            )
    else:
        st.warning("找不到符合篩選條件的資料，請嘗試不同的篩選項。")

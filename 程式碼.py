import pandas as pd
import os

# --- 請根據您的情況修改以下設定 ---

# 1. 包含所有月份狀態 Excel 檔案的資料夾路徑
monthly_reports_folder = r'I:\01.Sales Dept\Sales Manager\James\2.會議記錄\業檢會\2025\租車案件帳齡追蹤\每月延滯資料'

# 2. 包含案件編號和合約日期的底稿檔案路徑
master_list_file = r'I:\01.Sales Dept\Sales Manager\James\2.會議記錄\業檢會\2025\租車案件帳齡追蹤\案件編號底稿.xlsx'

# 3. 在底稿中，案件編號和合約日期的欄位名稱
case_id_col = '案件編號'
contract_date_col = '合約日期'

# 4. 在每個月的檔案中，案件編號和狀態的欄位名稱
monthly_case_id_col = '契約編號Contract No'
monthly_status_col = '''帳齡
Aging'''

# 5. 最終輸出的報表檔案名稱
# 取得腳本所在的目錄，並將輸出檔案設定在同一個資料夾
script_directory = os.path.dirname(os.path.realpath(__file__))
output_file = os.path.join(script_directory, 'consolidated_report_long.csv')

# 6. 最終報表的欄位名稱
final_col_case_id = '案件編號'
final_col_contract_date = '合約日期'
final_col_month = '月份'
final_col_status = '帳齡'


# --- 腳本主體 ---

def generate_long_report():
    """
    讀取底稿和各月份報告，合併成一張垂直格式的總表。
    每個案件在每個月的狀態都是獨立的一行。
    """
    try:
        # 讀取底稿 (案件編號、合約日期)
        master_df = pd.read_excel(master_list_file, engine='openpyxl')
        print(f"成功讀取底稿檔案: {master_list_file}")

        # 確保指定的欄位存在
        if case_id_col not in master_df.columns or contract_date_col not in master_df.columns:
            print(f"錯誤：底稿 '{master_list_file}' 中找不到 '{case_id_col}' 或 '{contract_date_col}' 欄位。")
            return

        # 將合約日期轉換為 YYYY/MM 格式
        try:
            # 根據使用者提供的 YYYYMM 格式來解析日期
            master_df[contract_date_col] = pd.to_datetime(master_df[contract_date_col], format='%Y%m', errors='coerce')
            # 移除無法成功解析日期的資料行
            master_df.dropna(subset=[contract_date_col], inplace=True)
            # 將日期格式化為 YYYY/MM
            master_df[contract_date_col] = master_df[contract_date_col].dt.strftime('%Y/%m')
            print("成功將合約日期轉換為 YYYY/MM 格式。")
        except Exception as e:
            print(f"警告：轉換合約日期格式時發生錯誤: {e}。將保留原始格式。")

        # 只保留案件編號和合約日期，並移除重複的案件
        master_df = master_df[[case_id_col, contract_date_col]].drop_duplicates(subset=[case_id_col])

        # 【核心修改】確保案件編號為字串格式，以利比對
        master_df[case_id_col] = master_df[case_id_col].astype(str)

        # 取得要在報告中包含的案件編號列表，使用 set 以加快查詢速度
        valid_case_ids = set(master_df[case_id_col])
        print(f"成功從底稿讀取 {len(valid_case_ids)} 個不重複的案件編號進行處理。")

        # 取得所有月份報告的檔案路徑，並排除Excel暫存檔(以~$開頭)
        monthly_files = [f for f in os.listdir(monthly_reports_folder) if f.endswith(('.xlsx', '.xls')) and not f.startswith('~$')]

        if not monthly_files:
            print(f"錯誤：在資料夾 '{monthly_reports_folder}' 中找不到任何 Excel 檔案。")
            return

        print(f"找到 {len(monthly_files)} 個月份的報告檔案。")

        all_months_data = []

        # 逐一讀取並處理月份報告
        for file_name in sorted(monthly_files):
            file_path = os.path.join(monthly_reports_folder, file_name)

            try:
                # 從檔名中擷取月份
                month_name_raw = os.path.basename(file_name).split('_')[0]

                # 將月份格式從 YYYYMM 轉為 YYYY/MM
                if len(month_name_raw) == 6 and month_name_raw.isdigit():
                    month_name = f"{month_name_raw[:4]}/{month_name_raw[4:]}"
                else:
                    month_name = month_name_raw # 如果格式不符，保留原始名稱

                print(f"正在處理檔案: {file_name}，月份設為: {month_name}")

                # 讀取月份報告，並指定第二列 (index=1) 為欄位名稱列
                monthly_df = pd.read_excel(file_path, engine='openpyxl', header=1)

                # 處理可能重複的欄位名稱
                if monthly_df.columns.duplicated().any():
                    monthly_df = monthly_df.loc[:, ~monthly_df.columns.duplicated()]

                # 確保月份報告中有必要的欄位
                if monthly_case_id_col not in monthly_df.columns or monthly_status_col not in monthly_df.columns:
                    print(f"警告：檔案 '{file_name}' 中找不到 '{monthly_case_id_col}' 或 '{monthly_status_col}' 欄位，將跳過此檔案。")
                    continue

                # 【核心修改】只保留存在於底稿案件列表中的資料
                original_count = len(monthly_df)
                monthly_df = monthly_df[monthly_df[monthly_case_id_col].isin(valid_case_ids)]
                filtered_count = len(monthly_df)
                if original_count > 0:
                    print(f"  -> 篩選結果: 在 {original_count} 筆資料中，找到 {filtered_count} 筆符合底稿的案件。")

                # 如果篩選後沒有資料，則跳過此檔案
                if monthly_df.empty:
                    continue

                # 篩選所需欄位並移除空值
                monthly_subset = monthly_df[[monthly_case_id_col, monthly_status_col]].dropna()

                # 新增月份欄位
                monthly_subset[final_col_month] = month_name

                # 重新命名欄位以進行合併
                monthly_subset = monthly_subset.rename(columns={
                    monthly_case_id_col: case_id_col,
                    monthly_status_col: final_col_status
                })

                all_months_data.append(monthly_subset)

            except Exception as e:
                print(f"處理檔案 {file_name} 時發生錯誤: {e}")

        if not all_months_data:
            print("沒有成功處理任何月份的資料，無法產生報表。")
            return

        # 將所有月份的資料合併成一個大的 DataFrame
        final_df = pd.concat(all_months_data, ignore_index=True)

        # 將月份資料與底稿合併，以加入合約日期
        final_df = pd.merge(final_df, master_df, on=case_id_col, how='left')

        # 重新排列欄位順序
        final_df = final_df[[case_id_col, contract_date_col, final_col_month, final_col_status]]

        # 重新命名最終的欄位
        final_df = final_df.rename(columns={
            case_id_col: final_col_case_id,
            contract_date_col: final_col_contract_date
        })

        # 儲存最終的合併報表
        final_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n報表產生完成！已儲存至: {os.path.abspath(output_file)}")

    except FileNotFoundError:
        print(f"錯誤：找不到指定的底稿檔案 '{master_list_file}'。請檢查路徑是否正確。")
    except Exception as e:
        print(f"發生未預期的錯誤: {e}")

# 執行函式
if __name__ == "__main__":
    generate_long_report()

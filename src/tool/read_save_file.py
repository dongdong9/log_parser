import traceback
from src.common_config import get_project_dir_path

import pandas as pd
def open_excel(input_file_path, sheet_name = "Sheet1", column_2_str = None):
    if input_file_path.endswith(".xlsx"):
        if sheet_name == "":
            if column_2_str is None:
                item_name_df = pd.read_excel(input_file_path)
            else:
                item_name_df = pd.read_excel(input_file_path, converters=column_2_str)
        else:
            if column_2_str is None:
                item_name_df = pd.read_excel(input_file_path, sheet_name)
            else:
                item_name_df = pd.read_excel(input_file_path, sheet_name, converters=column_2_str)
                #item_name_df = pd.read_excel(input_file_path, sheet_name)
    elif input_file_path.endswith(".csv"):
        try:
            item_name_df = pd.read_csv(input_file_path, encoding='utf-8',engine ='python')
        except:
            try:
                item_name_df = pd.read_csv(input_file_path, encoding='gb2312', engine='python')
            except:
                traceback.print_exc()
    else:
        print("input file type is not xlsx or csv")
        item_name_df = None
    return item_name_df


def save_dataframe(dataset_df, file_path, sheet_name ="Sheet1"):
    if file_path.endswith(".xlsx"):
        dataset_df.to_excel(file_path, index=False, sheet_name = sheet_name)
    elif file_path.endswith(".csv"):
        dataset_df.to_csv(file_path, index=False)
    else:
        print("file path is not end with .xlsx or .csv")
        return None
    cur_dir = get_project_dir_path()
    short_path = file_path.replace(cur_dir, "")
    print("finish to save data in {}".format(short_path))

def save_to_multi_sheet(file_path, dataframe_sheet_tuples):
    with pd.ExcelWriter(file_path) as writer:
        for dataset_df, sheet_name in dataframe_sheet_tuples:
            dataset_df.to_excel(writer,index=False,  sheet_name=sheet_name)
    print("finish to save result in {}".format(file_path))


def save_dataframe_by_csv(dataset_df, file_path):
    dataset_df.to_csv(file_path,index=False)
    cur_dir = get_project_dir_path()
    short_path = file_path.replace(cur_dir, "")
    print("finish to save data in {}".format(short_path))
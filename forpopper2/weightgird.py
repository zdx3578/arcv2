from dsl import objects
from dsl2 import grid2grid_fromgriddiff


def create_weight_grid(grid, base_weight=1):
    """
    创建一个与输入网格相同维度的权重网格，初始化为基础权重值

    参数:
        grid: 输入的2D网格（列表的列表）
        base_weight: 所有单元格的默认权重值

    返回:
        一个与输入相同维度的2D权重网格
    """
    if not grid:
        return []

    h, w = len(grid), len(grid[0])
    return [[base_weight for _ in range(w)] for _ in range(h)]



def apply_object_weights(grid, weight_grid, weight_increment=2, param_combinations=None):
    """
    对网格中属于对象的单元格应用权重增量，根据多种参数组合循环处理

    参数:
        grid: 输入的2D网格（列表的列表）
        weight_grid: 要更新的权重网格
        weight_increment: 对象单元格的权重增加值
        param_combinations: objects函数参数组合列表，每个组合为(univalued, diagonal, without_bg)的三元组
                            如果为None，将使用默认参数组合

    返回:
        更新后的包含对象权重的权重网格
    """
    # 如果未提供参数组合，使用默认组合
    if param_combinations is None:
        param_combinations = [
            (True, True, False),
            (True, False, False),
            (False, False, False),
            (False, True, False)
        ]

    # 遍历所有参数组合
    for univalued, diagonal, without_bg in param_combinations:
        objs = objects(grid, univalued, diagonal, without_bg)

        for obj in objs:
            for _, loc in obj:
                i, j = loc
                weight_grid[i][j] += weight_increment

    return weight_grid


def apply_difference_weights(grid1, grid2, weight_grid, weight_increment=15):
    """
    对两个网格之间不同的单元格应用权重增量

    参数:
        grid1: 第一个2D网格（列表的列表）
        grid2: 第二个2D网格（列表的列表）
        weight_grid: 要更新的权重网格
        weight_increment: 不同单元格的权重增加值

    返回:
        更新后的包含差异权重的权重网格
    """
    diff1, diff2 = grid2grid_fromgriddiff(grid1, grid2)

    if diff1 is None or diff2 is None:
        return weight_grid

    h, w = len(diff1), len(diff1[0])

    for i in range(h):
        for j in range(w):
            if diff1[i][j] is not None:  # 不同的单元格
                weight_grid[i][j] += weight_increment

    return weight_grid

def apply_custom_weight_rule(grid, weight_grid, rule_function, **kwargs):
    """
    对权重网格应用自定义权重规则

    参数:
        grid: 输入的2D网格（列表的列表）
        weight_grid: 要更新的权重网格
        rule_function: 一个接收grid、weight_grid和额外参数并返回更新后weight_grid的函数
        **kwargs: 传递给rule_function的额外参数

    返回:
        应用自定义规则后更新的权重网格
    """
    return rule_function(grid, weight_grid, **kwargs)

def location_based_weight_rule(grid, weight_grid, locations, weight_increment=5):
    """
    自定义规则示例：增加特定位置的权重

    参数:
        grid: 输入的2D网格（列表的列表）
        weight_grid: 要更新的权重网格
        locations: 要应用权重增量的坐标列表(i, j)
        weight_increment: 指定位置的权重增加值

    返回:
        更新后的权重网格
    """
    for i, j in locations:
        if 0 <= i < len(weight_grid) and 0 <= j < len(weight_grid[0]):
            weight_grid[i][j] += weight_increment

    return weight_grid

def pattern_based_weight_rule(grid, weight_grid, pattern_value, weight_increment=7):
    """
    自定义规则示例：增加与特定模式或值匹配的单元格的权重

    参数:
        grid: 输入的2D网格（列表的列表）
        weight_grid: 要更新的权重网格
        pattern_value: 网格中要匹配的值
        weight_increment: 匹配单元格的权重增加值

    返回:
        更新后的权重网格
    """
    for i in range(len(grid)):
        for j in range(len(grid[0])):
            if grid[i][j] == pattern_value:
                weight_grid[i][j] += weight_increment

    return weight_grid

def process_grid_with_weights(grid, grid2=None):
    """
    处理网格（或一对网格）并创建应用了所有规则的权重网格

    参数:
        grid: 主要的2D网格（列表的列表）
        grid2: 可选的第二个网格，用于差异计算

    返回:
        生成的权重网格
    """
    # 用基础权重1初始化权重网格
    weight_grid = create_weight_grid(grid, base_weight=0)

    # 应用对象权重（+10）
    weight_grid = apply_object_weights(grid, weight_grid, weight_increment=3)

    # 如果提供了grid2，应用差异权重（+15）
    if grid2 is not None:
        weight_grid = apply_difference_weights(grid, grid2, weight_grid, weight_increment=5)

    # 应用自定义规则的示例（可根据需要扩展）
    # weight_grid = apply_custom_weight_rule(grid, weight_grid, location_based_weight_rule,
    #                                        locations=[(0, 0), (1, 1)], weight_increment=5)

    return weight_grid




def normalize_weight_grid(weight_grid):
    """
    对权重网格进行归一化处理：
    1. 减去最小权重值
    2. 减去倒数第二小的权重值减1
    3. 将权重归一化到[0,1]区间

    参数:
        weight_grid: 待处理的权重网格

    返回:
        归一化后的权重网格
    """
    if not weight_grid or not weight_grid[0]:
        return weight_grid

    # 将二维权重网格转换为一维列表
    all_weights = [weight for row in weight_grid for weight in row]

    if not all_weights:
        return weight_grid

    # 排序找出最小值和倒数第二小的唯一值
    unique_weights = sorted(set(all_weights))

    # 如果只有一种权重值，直接返回全0网格
    if len(unique_weights) <= 1:
        return [[0 for _ in range(len(weight_grid[0]))] for _ in range(len(weight_grid))]

    # 获取最小值和倒数第二小的值
    min_weight = unique_weights[0]
    second_min_weight = unique_weights[1]

    # 第一步：减去最小权重
    adjusted_grid = [[weight - min_weight for weight in row] for row in weight_grid]

    # 第二步：减去(倒数第二小的权重-1)
    adjustment = second_min_weight - min_weight - 1
    if adjustment > 0:
        adjusted_grid = [[max(0, weight - adjustment) for weight in row] for row in adjusted_grid]

    # 找出调整后的最大值和最小值用于归一化
    adjusted_weights = [weight for row in adjusted_grid for weight in row]
    if not adjusted_weights or max(adjusted_weights) <= 0:
        return [[0 for _ in range(len(weight_grid[0]))] for _ in range(len(weight_grid))]

    max_adjusted = max(adjusted_weights)

    # 第三步：归一化到[0,1]区间
    normalized_grid = [[weight / max_adjusted if max_adjusted > 0 else 0 for weight in row] for row in adjusted_grid]

    return normalized_grid

def apply_weight_correction(weight_grid, scale_factor=10):
    """
    应用权重修正和缩放：
    1. 归一化权重
    2. 应用比例因子缩放到所需范围

    参数:
        weight_grid: 待处理的权重网格
        scale_factor: 缩放因子，默认为100（将归一化结果缩放到0-100区间）

    返回:
        修正后的权重网格
    """
    # 首先归一化
    normalized_grid = normalize_weight_grid(weight_grid)

    # 然后应用比例因子
    return [[weight * scale_factor for weight in row] for row in normalized_grid]


















from typing import List, Tuple, Optional, Union

def display_matrices(diff1: Union[List[Tuple[int, Tuple[int, int]]], List[List[Union[int, float]]]],
                    HW: Optional[list] = None,
                    diff2: Optional[Union[List[Tuple[int, Tuple[int, int]]], List[List[Union[int, float]]]]] = None,
                    diff3: Optional[Union[List[Tuple[int, Tuple[int, int]]], List[List[Union[int, float]]]]] = None,
                    is_grid_format: bool = False):
    """
    展示二维矩阵，支持两种输入格式：
    1. 元素和位置的元组列表 [(value, (row, col)), ...]
    2. 直接的二维网格 [[value, value, ...], [value, value, ...], ...]

    参数:
    - diff1: 必填，包含不同元素及其位置的集合或二维网格。
    - HW: 可选，矩阵的高和宽 [height, width]，如果不提供则自动计算。
    - diff2, diff3: 可选，额外的元素集合或二维网格。
    - is_grid_format: 指示输入是否为二维网格格式（True）或元组列表格式（False）。
    """
    if is_grid_format:
        # 如果输入是二维网格格式
        if not diff1:
            print("无内容")
            return

        max_row = len(diff1)
        max_col = len(diff1[0]) if max_row > 0 else 0

        # 初始化矩阵，转换第一个网格（跳过0值）
        matrix = [[' ' if cell == 0 or cell == 0.0 else str(int(cell)) if isinstance(cell, (int, float)) else str(cell) for cell in row] for row in diff1]

        # 如果有第二个网格，合并它（跳过0值）
        if diff2 and len(diff2) == max_row and len(diff2[0]) == max_col:
            for i in range(max_row):
                for j in range(max_col):
                    value = diff2[i][j]
                    if value != 0 and value != 0.0:
                        cell_str = str(int(value)) if isinstance(value, (int, float)) else str(value)
                        if matrix[i][j] == ' ':
                            matrix[i][j] = cell_str
                        else:
                            matrix[i][j] = matrix[i][j] + ',' + cell_str

        # 如果有第三个网格，也合并它（跳过0值）
        if diff3 and len(diff3) == max_row and len(diff3[0]) == max_col:
            for i in range(max_row):
                for j in range(max_col):
                    value = diff3[i][j]
                    if value != 0 and value != 0.0:
                        cell_str = str(int(value)) if isinstance(value, (int, float)) else str(value)
                        if matrix[i][j] == ' ':
                            matrix[i][j] = cell_str
                        else:
                            matrix[i][j] = matrix[i][j] + ',' + cell_str
    else:
        # 原来的元组列表处理逻辑
        # 合并所有不同元素的位置
        combined = list(diff1) + (diff2 if diff2 else []) + (diff3 if diff3 else [])

        if not combined:
            print("无差异")
            return

        # 确定矩阵的大小
        if HW:
            max_row, max_col = HW
        else:
            max_row = max(pos[0] for _, pos in combined) + 1
            max_col = max(pos[1] for _, pos in combined) + 1

        # 初始化空矩阵，初始内容为空格
        matrix = [[' ' for _ in range(max_col)] for _ in range(max_row)]

        # 填充矩阵：如果同一位置有多个值，则用逗号连接显示（跳过0值）
        for value, (row, col) in combined:
            if value == 0 or value == 0.0:
                continue
            current = matrix[row][col]
            # 对数值取整
            text = str(int(value)) if isinstance(value, (int, float)) else str(value)
            if current == ' ':
                matrix[row][col] = text
            else:
                matrix[row][col] = current + ',' + text

    # 打印带有边框的矩阵（没有竖列分割线）
    border = "+" + "-" * (max_col * 2 - 1) + "+"
    print(border)
    for row in matrix:
        print("|" + " ".join(row) + "|")
    print(border)

def display_weight_grid(weight_grid, title=None):
    """
    专门用于显示权重网格的函数，按照要求格式：
    - 整数显示（不带小数点）
    - 0值不显示
    - 没有竖列分割线
    - 列对齐

    参数:
    - weight_grid: 权重网格（二维列表）
    - title: 可选的标题
    """
    if not weight_grid or not weight_grid[0]:
        print("空网格")
        return

    if title:
        print(f"\n{title}")

    max_row = len(weight_grid)
    max_col = len(weight_grid[0])

    # 格式化网格（取整并跳过0值）
    formatted_grid = [[' ' for _ in range(max_col)] for _ in range(max_row)]

    # 计算每列的最大宽度
    col_widths = [0] * max_col
    for i, row in enumerate(weight_grid):
        for j, value in enumerate(row):
            if value != 0 and value != 0.0:
                value_str = str(int(value))
                formatted_grid[i][j] = value_str
                col_widths[j] = max(col_widths[j], len(value_str))

    # 确保每列至少有1个字符的宽度
    col_widths = [max(width, 1) for width in col_widths]

    # 打印表头
    total_width = sum(col_widths) + max_col - 1  # 总宽度加上每列之间的空格
    border = "+" + "-" * total_width + "+"
    print(border)

    # 打印数据，确保列对齐
    for row in formatted_grid:
        line = "|"
        for j, val in enumerate(row):
            # 右对齐填充空格
            line += val.rjust(col_widths[j]) + (" " if j < max_col - 1 else "")
        line += "|"
        print(line)

    # 打印表尾
    print(border)

    

# def display_weight_grid(weight_grid, title=None):
#     """
#     专门用于显示权重网格的函数，按照要求格式：
#     - 整数显示（不带小数点）
#     - 0值不显示
#     - 没有竖列分割线

#     参数:
#     - weight_grid: 权重网格（二维列表）
#     - title: 可选的标题
#     """
#     if not weight_grid or not weight_grid[0]:
#         print("空网格")
#         return

#     if title:
#         print(f"\n{title}")

#     max_row = len(weight_grid)
#     max_col = len(weight_grid[0])

#     # 格式化网格（取整并跳过0值）
#     formatted_grid = [[' ' for _ in range(max_col)] for _ in range(max_row)]
#     for i, row in enumerate(weight_grid):
#         for j, value in enumerate(row):
#             if value == 0 or value == 0.0:
#                 formatted_grid[i][j] = ' '
#             else:
#                 formatted_grid[i][j] = str(int(value))

#     # 打印表头
#     border = "+" + "-" * (max_col * 2 - 1) + "+"
#     print(border)

#     # 打印数据
#     for row in formatted_grid:
#         print("|" + " ".join(row) + "|")

#     # 打印表尾
#     print(border)

def visualize_weights_as_heatmap(weight_grid, title=None):
    """
    将权重网格可视化为一个简单的热图（使用ASCII字符）

    参数:
    - weight_grid: 权重网格（二维列表）
    - title: 可选的标题
    """
    if not weight_grid or not weight_grid[0]:
        print("空网格")
        return

    if title:
        print(f"\n{title}")

    # 找出最大和最小权重
    all_weights = [weight for row in weight_grid for weight in row if weight != 0]
    if not all_weights:
        print("所有单元格权重为0或空")
        return

    min_weight = min(all_weights)
    max_weight = max(all_weights)

    # 如果所有权重相同，无法显示热图
    if min_weight == max_weight:
        print(f"所有非零单元格权重相同: {int(min_weight)}")
        return

    # 创建权重到符号的映射
    heat_symbols = " ._-=+*#%@"  # 从低到高的强度

    # 创建热图
    heatmap = []
    for row in weight_grid:
        heat_row = []
        for weight in row:
            if weight == 0:
                heat_row.append(' ')
            else:
                # 归一化权重到0-1范围
                normalized = (weight - min_weight) / (max_weight - min_weight)
                # 映射到符号
                symbol_index = min(int(normalized * (len(heat_symbols) - 1)), len(heat_symbols) - 1)
                heat_row.append(heat_symbols[symbol_index])
        heatmap.append(heat_row)

    # 打印热图（带边框）
    border = "+" + "-" * (len(heatmap[0]) * 2 - 1) + "+"
    print(border)
    for row in heatmap:
        print("|" + " ".join(row) + "|")
    print(border)

    # 打印图例
    print("\n图例:")
    legend_steps = 5
    for i in range(legend_steps + 1):
        normalized = i / legend_steps
        symbol_index = min(int(normalized * (len(heat_symbols) - 1)), len(heat_symbols) - 1)
        value = min_weight + normalized * (max_weight - min_weight)
        print(f"{heat_symbols[symbol_index]}: ~{int(value)}")





# from typing import List, Tuple, Optional, Union
# import math

# def display_matrices(diff1: Union[List[Tuple[int, Tuple[int, int]]], List[List[Union[int, float]]]],
#                     HW: Optional[list] = None,
#                     diff2: Optional[Union[List[Tuple[int, Tuple[int, int]]], List[List[Union[int, float]]]]] = None,
#                     diff3: Optional[Union[List[Tuple[int, Tuple[int, int]]], List[List[Union[int, float]]]]] = None,
#                     is_grid_format: bool = False):
#     """
#     展示二维矩阵，支持两种输入格式：
#     1. 元素和位置的元组列表 [(value, (row, col)), ...]
#     2. 直接的二维网格 [[value, value, ...], [value, value, ...], ...]

#     参数:
#     - diff1: 必填，包含不同元素及其位置的集合或二维网格。
#     - HW: 可选，矩阵的高和宽 [height, width]，如果不提供则自动计算。
#     - diff2, diff3: 可选，额外的元素集合或二维网格。
#     - is_grid_format: 指示输入是否为二维网格格式（True）或元组列表格式（False）。
#     """
#     if is_grid_format:
#         # 如果输入是二维网格格式
#         if not diff1:
#             print("无内容")
#             return

#         max_row = len(diff1)
#         max_col = len(diff1[0]) if max_row > 0 else 0

#         # 初始化矩阵，复制第一个网格
#         matrix = [row[:] for row in diff1]

#         # 如果有第二个网格，合并它
#         if diff2 and len(diff2) == max_row and len(diff2[0]) == max_col:
#             for i in range(max_row):
#                 for j in range(max_col):
#                     if diff2[i][j] != ' ':
#                         if matrix[i][j] == ' ':
#                             matrix[i][j] = str(diff2[i][j])
#                         else:
#                             matrix[i][j] = str(matrix[i][j]) + ',' + str(diff2[i][j])

#         # 如果有第三个网格，也合并它
#         if diff3 and len(diff3) == max_row and len(diff3[0]) == max_col:
#             for i in range(max_row):
#                 for j in range(max_col):
#                     if diff3[i][j] != ' ':
#                         if matrix[i][j] == ' ':
#                             matrix[i][j] = str(diff3[i][j])
#                         else:
#                             matrix[i][j] = str(matrix[i][j]) + ',' + str(diff3[i][j])
#     else:
#         # 原来的元组列表处理逻辑
#         # 合并所有不同元素的位置
#         combined = list(diff1) + (diff2 if diff2 else []) + (diff3 if diff3 else [])

#         if not combined:
#             print("无差异")
#             return

#         # 确定矩阵的大小
#         if HW:
#             max_row, max_col = HW
#         else:
#             max_row = max(pos[0] for _, pos in combined) + 1
#             max_col = max(pos[1] for _, pos in combined) + 1

#         # 初始化空矩阵，初始内容为空格
#         matrix = [[' ' for _ in range(max_col)] for _ in range(max_row)]

#         # 填充矩阵：如果同一位置有多个值，则用逗号连接显示
#         for value, (row, col) in combined:
#             current = matrix[row][col]
#             text = str(value)
#             if current == ' ':
#                 matrix[row][col] = text
#             else:
#                 matrix[row][col] = current + ',' + text

#     # 处理矩阵元素以使其适合显示
#     formatted_matrix = []
#     for row in matrix:
#         formatted_row = []
#         for cell in row:
#             # 如果是数字，格式化为最多显示小数点后2位
#             if isinstance(cell, (int, float)):
#                 cell_str = f"{cell:.2f}" if isinstance(cell, float) else str(cell)
#                 # 截断长数字
#                 if len(cell_str) > 6:
#                     cell_str = cell_str[:6]
#             else:
#                 cell_str = str(cell)
#                 if len(cell_str) > 6:
#                     cell_str = cell_str[:6]
#             formatted_row.append(cell_str)
#         formatted_matrix.append(formatted_row)

#     # 确定每列的最大宽度
#     col_widths = []
#     for j in range(len(formatted_matrix[0])):
#         col_width = max(len(row[j]) for row in formatted_matrix)
#         col_widths.append(col_width)

#     # 打印带有边框的矩阵
#     horizontal_border = "+" + "+".join("-" * (width + 2) for width in col_widths) + "+"
#     print(horizontal_border)

#     for row in formatted_matrix:
#         formatted_cells = [f" {cell:{width}} " for cell, width in zip(row, col_widths)]
#         print("|" + "|".join(formatted_cells) + "|")

#     print(horizontal_border)

# def display_weight_grid(weight_grid, title=None, float_precision=2):
#     """
#     专门用于显示权重网格的函数

#     参数:
#     - weight_grid: 权重网格（二维列表）
#     - title: 可选的标题
#     - float_precision: 浮点数精度
#     """
#     if not weight_grid or not weight_grid[0]:
#         print("空网格")
#         return

#     if title:
#         print(f"\n{title}")

#     max_row = len(weight_grid)
#     max_col = len(weight_grid[0])

#     # 格式化网格
#     formatted_grid = []
#     for row in weight_grid:
#         formatted_row = []
#         for value in row:
#             if isinstance(value, float):
#                 # 格式化浮点数
#                 formatted_value = f"{value:.{float_precision}f}"
#             else:
#                 formatted_value = str(value)
#             formatted_row.append(formatted_value)
#         formatted_grid.append(formatted_row)

#     # 确定每列的最大宽度
#     col_widths = []
#     for j in range(max_col):
#         col_width = max(len(row[j]) for row in formatted_grid)
#         col_widths.append(col_width)

#     # 打印表头
#     header = "+" + "+".join("-" * (width + 2) for width in col_widths) + "+"
#     print(header)

#     # 打印行索引和数据
#     for i, row in enumerate(formatted_grid):
#         row_str = "|"
#         for j, (cell, width) in enumerate(zip(row, col_widths)):
#             row_str += f" {cell:>{width}} |"
#         print(row_str)

#     # 打印表尾
#     print(header)

# def visualize_weights_as_heatmap(weight_grid, title=None):
#     """
#     将权重网格可视化为一个简单的热图（使用ASCII字符）

#     参数:
#     - weight_grid: 权重网格（二维列表）
#     - title: 可选的标题
#     """
#     if not weight_grid or not weight_grid[0]:
#         print("空网格")
#         return

#     if title:
#         print(f"\n{title}")

#     # 找出最大和最小权重
#     all_weights = [weight for row in weight_grid for weight in row]
#     min_weight = min(all_weights)
#     max_weight = max(all_weights)

#     # 如果所有权重相同，无法显示热图
#     if min_weight == max_weight:
#         print(f"所有单元格权重相同: {min_weight}")
#         return

#     # 创建权重到符号的映射
#     heat_symbols = " ._-=+*#%@"  # 从低到高的强度

#     # 创建热图
#     heatmap = []
#     for row in weight_grid:
#         heat_row = []
#         for weight in row:
#             # 归一化权重到0-1范围
#             normalized = (weight - min_weight) / (max_weight - min_weight)
#             # 映射到符号
#             symbol_index = min(int(normalized * len(heat_symbols)), len(heat_symbols) - 1)
#             heat_row.append(heat_symbols[symbol_index])
#         heatmap.append(heat_row)

#     # 打印热图
#     print(f"热图 (权重范围: {min_weight:.2f} - {max_weight:.2f}):")
#     for row in heatmap:
#         print("".join(row))

#     # 打印图例
#     print("\n图例:")
#     legend_steps = 5
#     for i in range(legend_steps + 1):
#         normalized = i / legend_steps
#         symbol_index = min(int(normalized * len(heat_symbols)), len(heat_symbols) - 1)
#         value = min_weight + normalized * (max_weight - min_weight)
#         print(f"{heat_symbols[symbol_index]}: ~{value:.2f}")












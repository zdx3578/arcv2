from dsl import objects
from dsl2 import *
from objutil import *


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

def determine_grid_type(grid_id):
    """
    根据网格ID确定其类型

    参数:
        grid_id: 网格ID字符串

    返回:
        网格类型标识: "in", "out", "diff" 或 "unknown"
    """
    if "input" in grid_id:
        return "in"
    elif "output" in grid_id:
        return "out"
    elif "diff" in grid_id:
        return "diff"
    else:
        return "unknown"  # 默认情况处理

def apply_object_weights_for_arc_task(task, weight_increment=2, pixel_threshold_pct=60,  param_combinations=None):
    """
    对整个ARC任务的训练数据和测试数据的输入网格应用权重分析，
    找出所有网格中相同形状的对象并进行权重设置

    参数:
        task: ARC任务数据，包含'train'和'test'两部分
        weight_increment: 对象单元格的基础权重增加值
        param_combinations: objects函数参数组合列表，每个组合为(univalued, diagonal, without_bg)的三元组
                          如果为None，将使用默认参数组合

    返回:
        包含所有输入和输出网格权重的字典
    """

    diff_weight_increment = 5

    if param_combinations is None:
        param_combinations = [
            (True, True, False),
            (True, False, False),
            (False, False, False),
            (False, True, False)
        ]

    # 获取训练数据和测试数据
    train_data = task['train']
    test_data = task['test']

    # 创建一个存储所有网格和对象的字典
    all_grids = {
        'train_inputs': [],  # [(pair_id, grid), ...]
        'train_diffs': [],   # [(pair_id, grid), ...]
        'train_outputs': [], # [(pair_id, grid), ...]
        'test_inputs': []    # [(pair_id, grid), ...]
    }

    # 初始化对象集和权重网格
    object_sets = {}
    weight_grids = {}

    # 收集所有网格
    for pair_id, data_pair in enumerate(train_data):
        I = data_pair['input']
        O = data_pair['output']
        I = tuple(tuple(row) for row in I)
        O = tuple(tuple(row) for row in O)

        diff_i_to_o, diff_o_to_i = grid2grid_fromgriddiff(I, O)

        # 添加到网格集合
        all_grids['train_inputs'].append((pair_id, I))
        all_grids['train_outputs'].append((pair_id, O))

        all_grids['train_diffs'].append((pair_id, diff_i_to_o))

        # 初始化权重网格
        weight_grids[f'train_input_{pair_id}'] = [[0 for _ in range(len(I[0]))] for _ in range(len(I))]
        weight_grids[f'train_output_{pair_id}'] = [[0 for _ in range(len(O[0]))] for _ in range(len(O))]

    for test_id, test_case in enumerate(test_data):
        test_input = test_case['input']
        all_grids['test_inputs'].append((test_id, test_input))
        weight_grids[f'test_input_{test_id}'] = [[0 for _ in range(len(test_input[0]))] for _ in range(len(test_input))]



    # 步骤1：生成所有网格的对象集
    for grid_type in all_grids:
        for idx, grid in all_grids[grid_type]:
            grid_id = f"{grid_type.rstrip('s')}_{idx}"  # 例如 'train_input_0'
            height, width = len(grid), len(grid[0]) if grid else 0

            # 确定in_or_out参数
            # in_or_out = "in" if "input" in grid_id else "out"
            in_or_out = determine_grid_type(grid_id)


            # 生成对象集
            object_sets[f"{in_or_out}_obj_set_{grid_id}"] = all_pureobjects_from_grid(param_combinations=param_combinations,
                the_pair_id=idx, in_or_out=in_or_out, grid=grid, hw=(height, width)
            )

    # 步骤2：为所有对象设置基本权重
    for grid_type in all_grids:
        for idx, grid in all_grids[grid_type]:
            grid_id = f"{grid_type.rstrip('s')}_{idx}"
            # in_or_out = "in" if "input" in grid_id else "out"
            in_or_out = determine_grid_type(grid_id)

            if in_or_out == "diff":
                continue


            # 获取对象集
            obj_set_key = f"{in_or_out}_obj_set_{grid_id}"
            if obj_set_key not in object_sets:
                continue

            # 为对象设置基本权重
            for obj in object_sets[obj_set_key]:
                for value, loc in obj:
                    i, j = loc
                    weight_grids[grid_id][i][j] += weight_increment

    # # 步骤3：创建所有对象的规范化形状字典
    # normalized_shapes = {}  # {规范化形状: [(网格ID, 原始对象, 对象类型)]}
    # for grid_type in all_grids:
    #     for idx, grid in all_grids[grid_type]:
    #         grid_id = f"{grid_type.rstrip('s')}_{idx}"
    #         in_or_out = "in" if "input" in grid_id else "out"

    #         obj_set_key = f"{in_or_out}_obj_set_{grid_id}"
    #         if obj_set_key not in object_sets:
    #             continue

    #         for obj in object_sets[obj_set_key]:
    #             normalized_obj = shift_pure_obj_to_0_0_0(obj)  # 获取规范化形状

    #             if normalized_obj not in normalized_shapes:
    #                 normalized_shapes[normalized_obj] = []
    #             normalized_shapes[normalized_obj].append((grid_id, obj, in_or_out))


    # 步骤3：创建所有对象的规范化形状字典
    normalized_shapes = {}  # {规范化形状: [(网格ID, 原始对象, 对象类型)]}

    for grid_type in all_grids:
        for idx, grid in all_grids[grid_type]:
            grid_id = f"{grid_type.rstrip('s')}_{idx}"
            # in_or_out = "in" if "input" in grid_id else "out"
            in_or_out = determine_grid_type(grid_id)


            obj_set_key = f"{in_or_out}_obj_set_{grid_id}"
            if obj_set_key not in object_sets:
                continue

            # 如果 normalized_obj 是包含 (value, (i, j)) 元素的集合
            for obj in object_sets[obj_set_key]:
                # 获取规范化形状
                normalized_obj = shift_pure_obj_to_0_0_0(obj)

                # 将集合中的元素转换为可排序的元组列表
                # 将每个 (value, (i, j)) 转换为 (value, i, j)
                sorted_elements = []
                for value, loc in normalized_obj:
                    i, j = loc
                    sorted_elements.append((value, i, j))

                # 排序并创建可哈希的表示
                hashable_obj = tuple(sorted(sorted_elements))

                if hashable_obj not in normalized_shapes:
                    normalized_shapes[hashable_obj] = []
                normalized_shapes[hashable_obj].append((grid_id, obj, in_or_out))

    # 步骤4：根据相同形状的对象数量增加权重
    for shape, obj_list in normalized_shapes.items():
        num_objects = len(obj_list)

        if num_objects > 1:  # 至少有两个相同形状的对象
            # 为所有相同形状的对象增加相应权重
            shape_bonus = num_objects  # 相同形状的对象数量作为额外权重

            for grid_id, obj, _ in obj_list:
                in_or_out = determine_grid_type(grid_id)
                if in_or_out == "diff":
                    continue

                for _, loc in obj:
                    i, j = loc
                    weight_grids[grid_id][i][j] += shape_bonus


    # 步骤5：分析相同颜色并调整权重
    apply_color_matching_weights(normalized_shapes, weight_grids, all_grids, pixel_threshold_pct)




    # 步骤0：应用网格差异权重（优化版）
    for pair_id, data_pair in enumerate(train_data):
        I = data_pair['input']
        O = data_pair['output']
        I = tuple(tuple(row) for row in I)
        O = tuple(tuple(row) for row in O)

        # 获取网格的尺寸
        rows_i, cols_i = len(I), len(I[0])
        rows_o, cols_o = len(O), len(O[0])

        # 检查尺寸是否相同（适用grid2grid_fromgriddiff函数的要求）
        if rows_i == rows_o and cols_i == cols_o:
            # 生成差异网格
            diff_i_to_o, diff_o_to_i = grid2grid_fromgriddiff(I, O)

            if diff_i_to_o is not None and diff_o_to_i is not None:
                # 创建差异权重网格
                diff_weight_grid = [[0 for _ in range(cols_i)] for _ in range(rows_i)]

                # 填充差异权重
                for i in range(rows_i):
                    for j in range(cols_i):
                        if diff_i_to_o[i][j] is not None:  # 发现差异
                            diff_weight_grid[i][j] = diff_weight_increment

                # 将差异权重网格添加到输入和输出权重网格
                weight_grids[f'train_input_{pair_id}'] = add_weight_grids(
                    weight_grids[f'train_input_{pair_id}'], diff_weight_grid
                )
                weight_grids[f'train_output_{pair_id}'] = add_weight_grids(
                    weight_grids[f'train_output_{pair_id}'], diff_weight_grid
                )
        else:
            # 对于尺寸不同的网格，我们不能直接使用grid2grid_fromgriddiff
            # 这里可以添加额外的处理逻辑，或者简单地跳过
            # 例如，使用其他方法计算差异，或者直接使用原始网格
            raise ValueError(
                f"输入网格和输出网格的尺寸不匹配: {rows_i}x{cols_i} vs {rows_o}x{cols_o}"
            )


    return weight_grids


# 步骤6：分析相同颜色并调整权重（优化版 - 添加像素占比阈值）
def apply_color_matching_weights(normalized_shapes, weight_grids, all_grids, pixel_threshold_pct=50):
    """
    分析相同形状的对象中的相同颜色，并根据权重调整，同时考虑颜色占比阈值

    参数:
        normalized_shapes: 规范化形状字典
        weight_grids: 权重网格字典
        all_grids: 所有网格的字典
        pixel_threshold_pct: 颜色占比阈值百分比，超过此阈值的颜色会被特殊处理
    """
    for shape, obj_list in normalized_shapes.items():
        if len(obj_list) <= 1:
            continue  # 跳过没有匹配的形状

        # 按对象权重合计排序
        obj_with_weights = []
        for grid_id, obj, obj_type in obj_list:
            in_or_out = determine_grid_type(grid_id)
            if in_or_out == "diff":
                continue
            # 从grid_id获取实际网格，以便计算总像素数
            grid_type, idx = grid_id.rsplit('_', 1)
            grid_type += 's'  # 恢复复数形式，例如 'train_input' -> 'train_inputs'
            idx = int(idx)

            # 获取网格尺寸
            _, grid = next((g for g in all_grids[grid_type] if g[0] == idx), (None, None))
            if grid is None:
                continue

            height, width = len(grid), len(grid[0]) if grid else 0
            total_pixels = height * width

            # 计算每种颜色的像素数量
            color_counts = {}
            for color, _ in obj:
                if color not in color_counts:
                    color_counts[color] = 0
                color_counts[color] += 1

            # 计算权重总和
            weight_sum = sum(weight_grids[grid_id][i][j] for _, (i, j) in obj)

            # 保存对象信息、权重和颜色统计
            obj_with_weights.append((grid_id, obj, obj_type, weight_sum, color_counts, total_pixels))

        # 按权重降序排列
        obj_with_weights.sort(key=lambda x: x[3], reverse=True)

        # 分析相同颜色
        for i in range(len(obj_with_weights)):
            high_grid_id, high_obj, high_type, high_weight, high_color_counts, high_total_pixels = obj_with_weights[i]

            # 预处理高权重对象的颜色索引
            high_obj_by_color = {}
            high_color_max_weights = {}

            # 为每种颜色创建索引并计算最大权重
            for high_val, high_loc in high_obj:
                if high_val not in high_obj_by_color:
                    high_obj_by_color[high_val] = []
                    high_color_max_weights[high_val] = 0

                hi, hj = high_loc
                current_weight = weight_grids[high_grid_id][hi][hj]
                high_obj_by_color[high_val].append((high_loc, current_weight))
                high_color_max_weights[high_val] = max(high_color_max_weights[high_val], current_weight)

            for j in range(i+1, len(obj_with_weights)):
                low_grid_id, low_obj, low_type, low_weight, low_color_counts, low_total_pixels = obj_with_weights[j]

                # 预处理低权重对象的颜色索引
                low_obj_by_color = {}
                for low_val, low_loc in low_obj:
                    if low_val not in low_obj_by_color:
                        low_obj_by_color[low_val] = []
                    low_obj_by_color[low_val].append(low_loc)

                # 获取两个对象共有的颜色
                common_colors = set(high_obj_by_color.keys()) & set(low_obj_by_color.keys())

                if common_colors:  # 有共有颜色
                    for color in common_colors:
                        # 检查高权重对象中该颜色的占比
                        high_color_pct = (high_color_counts.get(color, 0) / high_total_pixels) * 100
                        # 检查低权重对象中该颜色的占比
                        low_color_pct = (low_color_counts.get(color, 0) / low_total_pixels) * 100

                        # 如果任一对象中该颜色占比超过阈值，则将该颜色区域的权重归零
                        if high_color_pct > pixel_threshold_pct or low_color_pct > pixel_threshold_pct:
                            # 将高权重对象中该颜色的权重归零
                            for (hi, hj), _ in high_obj_by_color[color]:
                                weight_grids[high_grid_id][hi][hj] = 0

                            # 将低权重对象中该颜色的权重归零
                            for li, lj in low_obj_by_color[color]:
                                weight_grids[low_grid_id][li][lj] = 0
                        else:
                            # 对于占比不超过阈值的颜色，更新低权重对象中的权重
                            target_weight = int(high_color_max_weights[color])
                            for li, lj in low_obj_by_color[color]:
                                if weight_grids[low_grid_id][li][lj] < target_weight:
                                    weight_grids[low_grid_id][li][lj] = target_weight




def has_matching_colors(obj1, obj2):
    """
    检查两个对象是否有相同颜色的部分

    参数:
        obj1: 第一个对象，格式为 [(value, location), ...]
        obj2: 第二个对象，格式为 [(value, location), ...]

    返回:
        如果有相同颜色的部分，返回True；否则返回False
    """
    colors1 = set(val for val, _ in obj1)
    colors2 = set(val for val, _ in obj2)

    # 检查是否有共同的颜色
    return bool(colors1.intersection(colors2))


def process_grid_with_weights(task):
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
    # weight_grid = apply_object_weights(grid, weight_grid, weight_increment=3)

    # 调用示例
    weight_grid_in = apply_object_weights(grid, "in", weight_grid, weight_increment=3)
    weight_grid_out = apply_object_weights(grid2, "out", weight_grid, weight_increment=2)

    # 如果提供了grid2，应用差异权重（+15）
    if grid2 is not None:
        diff_weight_grid = apply_difference_weights(grid, grid2, weight_grid, weight_increment=5)

    # 应用自定义规则的示例（可根据需要扩展）
    # weight_grid = apply_custom_weight_rule(grid, weight_grid, location_based_weight_rule,
    #                                        locations=[(0, 0), (1, 1)], weight_increment=5)
    weight_grid_in = add_weight_grids(weight_grid_in, diff_weight_grid)
    weight_grid_out = add_weight_grids(weight_grid_out, diff_weight_grid)

    return weight_grid_in, weight_grid_out



def apply_object_weights(grid_pair, object_sets, in_weight_grid, out_weight_grid, weight_increment=2, param_combinations=None):
    """
    对单个网格对中属于对象的单元格应用权重增量

    参数:
        grid_pair: 包含输入和输出网格的元组(I, O)
        object_sets: 包含所有对象集合的字典，使用格式 "in_obj_set_{pair_id}" 和 "out_obj_set_{pair_id}"
        in_weight_grid: 输入网格的权重矩阵
        out_weight_grid: 输出网格的权重矩阵
        weight_increment: 对象单元格的权重增加值
        param_combinations: objects函数参数组合列表

    返回:
        更新后的包含对象权重的权重网格元组 (in_weight_grid, out_weight_grid)
    """
    # 创建一个临时任务结构
    temp_task = {
        'train': [{'input': grid_pair[0], 'output': grid_pair[1]}],
        'test': []
    }

    # 调用完整版函数
    weight_grids = apply_object_weights_for_arc_task(temp_task, weight_increment, param_combinations)

    # 返回更新后的权重网格
    return weight_grids['train_input_0'], weight_grids['train_output_0']


def apply_difference_weights(grid1, grid2, weight_grid, weight_increment=5):
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



def add_weight_grids(grid1, grid2):
    """
    将两个权重网格的对应元素相加

    参数:
        grid1: 第一个权重网格
        grid2: 第二个权重网格

    返回:
        新的权重网格，每个元素是对应位置元素的和
    """
    if not grid1 or not grid1[0]:
        return grid2
    if not grid2 or not grid2[0]:
        return grid1

    # 确保两个网格尺寸相同
    if len(grid1) != len(grid2) or len(grid1[0]) != len(grid2[0]):
        raise ValueError("两个权重网格的尺寸必须相同")

    # 创建新网格，存储相加后的结果
    result = []
    for i in range(len(grid1)):
        row = []
        for j in range(len(grid1[0])):
            row.append(grid1[i][j] + grid2[i][j])
        result.append(row)

    return result


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

    # 第三步：归一化到[1-9  0,1]区间
    # normalized_grid = [[weight / max_adjusted if max_adjusted > 0 else 0 for weight in row] for row in adjusted_grid]
    # 第三步：直接归一化到[1,9]区间
    # 第三步：将非零元素归一化到[1,9]区间，保留零元素为零
    normalized_grid = [[1 + (weight / max_adjusted * 8) if weight > 0 and max_adjusted > 0 else 0 if weight == 0 else 1
                        for weight in row] for row in adjusted_grid]
    # 整数化
    normalized_gridint = [[int(1 + (weight / max_adjusted * 8)) if weight > 0 and max_adjusted > 0 else 0 if weight == 0 else 1
                            for weight in row] for row in adjusted_grid]

    return normalized_grid,normalized_gridint
    # return adjusted_grid, adjusted_grid

def apply_weight_correction(weight_grid, scale_factor=9):
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
















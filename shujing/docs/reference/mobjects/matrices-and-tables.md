---
title: "矩阵和表格"
description: "行列中的条目：括号之间的矩阵、线条之间的表格，条目可以是数字、数学、文字或任何 mobject。"
---

# 矩阵和表格

```python fold title="影片代码"
import manimgx as m


class MatricesAndTablesHero(m.Scene):
    def construct(self) -> None:
        matrix = m.Matrix([[2, 0], [1, 3]])
        matrix.set_column_colors(m.YELLOW, m.BLUE)
        table = m.Table(
            [["1", "2"], ["4", "8"]],
            row_labels=[m.Text("x"), m.Text("2ˣ")],
            col_labels=[m.Text("a"), m.Text("b")],
        ).scale(0.7)
        m.VGroup(matrix, table).arrange(buff=1.5)
        self.play(m.Write(matrix))
        self.play(table.create())
        self.wait()
```

矩阵和表格在行列中容纳条目：矩阵在括号之间，表格
在线条之间，如果提供则带有行列标签。以值的形式给出条目，每种
矩阵或表格会创建对应的 mobject：数字、整数、数学、
文字，或 mobject 本身。每一行、每一列和每个条目都是一个 mobject，可以
着色和动画化。

::: manimgx.Matrix
    options:
      heading_level: 2
      inherited_members: [entry, entry_config, cells, get_rows, get_columns, set_row_colors, set_column_colors]

::: manimgx.DecimalMatrix
    options:
      heading_level: 3

::: manimgx.IntegerMatrix
    options:
      heading_level: 3

::: manimgx.MobjectMatrix
    options:
      heading_level: 3

::: manimgx.Table
    options:
      heading_level: 2
      inherited_members: [entry, entry_config, cells, get_rows, get_columns, set_row_colors, set_column_colors]

::: manimgx.DecimalTable
    options:
      heading_level: 3

::: manimgx.IntegerTable
    options:
      heading_level: 3

::: manimgx.MathTable
    options:
      heading_level: 3

::: manimgx.MobjectTable
    options:
      heading_level: 3